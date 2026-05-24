"""Background workflow run execution."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update

from app.database import async_session
from app.models import (
    AppSettings,
    PlaybookSettings,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunMessage,
)
from app.services.ai.registry import get_provider
from app.services.ai.tools import TOOL_DEFINITIONS, create_tool_executor
from app.services.browser import close_browser_context, create_browser_session_from_settings
from app.services.prompts import render_prompt

logger = logging.getLogger(__name__)

_running_workflow_runs: dict[int, asyncio.Task] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _tool_definitions_for(tool_names: list[str]) -> list[dict]:
    allowed = set(tool_names)
    return [
        tool
        for tool in TOOL_DEFINITIONS
        if tool.get("function", {}).get("name") in allowed
    ]


async def _settings_dict() -> dict[str, str]:
    async with async_session() as db:
        result = await db.execute(select(AppSettings))
        return {row.key: row.value or "" for row in result.scalars().all()}


async def _next_sequence(run_id: int) -> int:
    async with async_session() as db:
        result = await db.execute(
            select(WorkflowRunMessage.sequence)
            .where(WorkflowRunMessage.run_id == run_id)
            .order_by(WorkflowRunMessage.sequence.desc())
            .limit(1)
        )
        return (result.scalar_one_or_none() or 0) + 1


async def _persist_message(run_id: int, sequence: int, msg: dict) -> None:
    async with async_session() as db:
        db.add(
            WorkflowRunMessage(
                run_id=run_id,
                sequence=sequence,
                role=msg["role"],
                content=msg.get("content"),
                tool_name=msg.get("tool_name"),
                tool_call_id=msg.get("tool_call_id"),
                metadata_json=(
                    json.dumps(msg.get("metadata")) if msg.get("metadata") else None
                ),
            )
        )
        await db.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .values(updated_at=_utcnow())
        )
        await db.commit()


async def create_and_start_workflow_run(
    workflow_id: int,
    variables: dict[str, str] | None = None,
) -> int:
    """Create a run, persist initial messages, schedule execution, and return the run id."""
    variables = variables or {}
    settings = await _settings_dict()
    provider_name = (settings.get("default_provider") or "openai").strip() or "openai"
    model = (settings.get("default_model") or "gpt-4o").strip() or "gpt-4o"

    async with async_session() as db:
        workflow = await db.get(WorkflowDefinition, workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        playbook_result = await db.execute(
            select(PlaybookSettings).where(
                PlaybookSettings.playbook_name == workflow.playbook_name
            )
        )
        playbook = playbook_result.scalar_one_or_none()
        system_prompt = playbook.system_prompt if playbook else ""
        user_prompt = render_prompt(workflow.user_prompt_template, variables)

        run = WorkflowRun(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status="running",
            provider=provider_name,
            model=model,
            started_at=_utcnow(),
            updated_at=_utcnow(),
            variables_json=json.dumps(variables),
        )
        db.add(run)
        await db.flush()

        db.add_all(
            [
                WorkflowRunMessage(
                    run_id=run.id,
                    sequence=1,
                    role="system",
                    content=system_prompt,
                ),
                WorkflowRunMessage(
                    run_id=run.id,
                    sequence=2,
                    role="user",
                    content=user_prompt,
                ),
            ]
        )
        await db.commit()
        run_id = run.id

    start_workflow_run(run_id)
    return run_id


def start_workflow_run(run_id: int) -> None:
    """Schedule a workflow run continuation in the current event loop."""
    task = asyncio.create_task(_run_workflow(run_id))
    _running_workflow_runs[run_id] = task
    task.add_done_callback(lambda _task: _running_workflow_runs.pop(run_id, None))


def cancel_workflow_run(run_id: int) -> None:
    """Cancel an in-process workflow run task if it is still active."""
    task = _running_workflow_runs.pop(run_id, None)
    if task and not task.done():
        task.cancel()


async def delete_workflow_run(run_id: int) -> None:
    """Delete a workflow run and its persisted messages."""
    cancel_workflow_run(run_id)
    async with async_session() as db:
        await db.execute(
            delete(WorkflowRunMessage).where(WorkflowRunMessage.run_id == run_id)
        )
        await db.execute(delete(WorkflowRun).where(WorkflowRun.id == run_id))
        await db.commit()


async def delete_workflow_runs_for_workflow(workflow_id: int) -> None:
    """Delete all runs and messages for a workflow."""
    async with async_session() as db:
        result = await db.execute(
            select(WorkflowRun.id).where(WorkflowRun.workflow_id == workflow_id)
        )
        run_ids = list(result.scalars().all())
        for run_id in run_ids:
            cancel_workflow_run(run_id)
        if run_ids:
            await db.execute(
                delete(WorkflowRunMessage).where(
                    WorkflowRunMessage.run_id.in_(run_ids)
                )
            )
            await db.execute(delete(WorkflowRun).where(WorkflowRun.id.in_(run_ids)))
        await db.commit()


async def resume_workflow_run(run_id: int, user_message: str) -> None:
    """Append a user message and continue a completed/error run in the background."""
    sequence = await _next_sequence(run_id)
    await _persist_message(run_id, sequence, {"role": "user", "content": user_message})
    async with async_session() as db:
        await db.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .values(status="running", error=None, ended_at=None, updated_at=_utcnow())
        )
        await db.commit()
    start_workflow_run(run_id)


async def mark_stale_running_runs() -> None:
    """Mark runs left running by a prior server process as errored."""
    async with async_session() as db:
        await db.execute(
            update(WorkflowRun)
            .where(WorkflowRun.status == "running")
            .values(
                status="error",
                error="Server restarted while this workflow run was active.",
                ended_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )
        await db.commit()


async def _run_workflow(run_id: int) -> None:
    """Run or resume the provider tool-calling loop for a workflow run."""
    settings = await _settings_dict()

    async with async_session() as db:
        run = await db.get(WorkflowRun, run_id)
        if not run:
            return
        workflow = await db.get(WorkflowDefinition, run.workflow_id)
        if not workflow:
            await db.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == run_id)
                .values(
                    status="error",
                    error="Workflow definition not found.",
                    ended_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
            await db.commit()
            return

        message_result = await db.execute(
            select(WorkflowRunMessage)
            .where(WorkflowRunMessage.run_id == run_id)
            .order_by(WorkflowRunMessage.sequence)
        )
        messages = [
            {
                "role": msg.role,
                "content": msg.content or "",
                **({"tool_name": msg.tool_name} if msg.tool_name else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
            }
            for msg in message_result.scalars().all()
        ]
        allowed_tools = json.loads(workflow.allowed_tools_json or "[]")

    sequence_counter = [len(messages)]

    async def on_message(msg: dict) -> None:
        sequence_counter[0] += 1
        await _persist_message(run_id, sequence_counter[0], msg)

    pw = None
    browser_ctx = None
    browser_tmp_dir = None
    browser_is_cdp = False
    cdp_url = (settings.get("chrome_cdp_url") or "").strip()
    chrome_path = (settings.get("chrome_profile_path") or "").strip()

    if cdp_url or chrome_path:
        try:
            pw, browser_ctx, browser_tmp_dir, browser_is_cdp = (
                await create_browser_session_from_settings(settings)
            )
        except Exception:
            logger.exception("Workflow run %s: failed to create browser context", run_id)
            pw, browser_ctx, browser_tmp_dir = None, None, None
            browser_is_cdp = False

    try:
        provider = get_provider(run.provider, settings)
        result = await provider.run_thread(
            messages=messages,
            model=run.model,
            tools=_tool_definitions_for(allowed_tools),
            tool_executor=create_tool_executor(browser_context=browser_ctx),
            on_message=on_message,
        )
        async with async_session() as db:
            await db.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == run_id)
                .values(status="done", error=None, ended_at=_utcnow(), updated_at=_utcnow())
            )
            await db.commit()
        logger.info("Workflow run %s completed: %s", run_id, (result or {}).get("content", "")[:80])
    except Exception as exc:
        logger.exception("Workflow run %s failed", run_id)
        async with async_session() as db:
            await db.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == run_id)
                .values(
                    status="error",
                    error=str(exc),
                    ended_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
            await db.commit()
    finally:
        if browser_ctx:
            await close_browser_context(
                pw, browser_ctx, browser_tmp_dir, is_cdp=browser_is_cdp
            )
