"""LLM-powered analysis of completed workflow runs for fixes and prompt improvements."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import (
    AppSettings,
    PlaybookSettings,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunMessage,
)
from app.services.ai.registry import get_provider

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_CHARS = 80_000
TOOL_RESULT_TRUNCATE = 4_000
TOOL_RESULT_HEAD_TAIL = 2_000

RUN_FIX_SYSTEM_PROMPT = """You are an expert reviewer for Intelligence Engine workflow runs. Intelligence Engine is a local PoC that runs user-defined workflows: a Runtime Algorithm system prompt, a Mustache user prompt template, and a set of allowed agent tools. Each run persists a full chat transcript (system, user, assistant, tool_call, tool_result).

Your job is to analyze one completed or failed run and help the human operator fix problems and improve the workflow for the next run.

## Platform facts (use in your reasoning)

- Paths in prompts may be relative; they resolve against INTELLIGENCE_ENGINE_HOME_DIR (app home), not the user's home directory unless configured.
- Local filesystem tools:
  - list_local_folder — list a directory
  - read_local_folder — read all supported files in a directory (one level, non-recursive)
  - read_local_file — read a single file (must include extension)
  - read_local_path — file or directory (auto-dispatch)
- browse_page requires Chrome remote debugging (CDP URL) in Settings.
- fetch_url is HTTP-only (no JavaScript). web_search uses DuckDuckGo.
- Tool errors returned as plain text in tool_result messages are authoritative; do not assume success.
- A run-level error field (if present) means the background runner failed outside a single tool call.

## What to analyze

1. Run outcome: success, failure, or incomplete reasoning.
2. Tool-call patterns: wrong tool for the job, repeated failures, path mistakes (file vs folder, missing extension, empty folder, typos).
3. Configuration gaps: missing API keys, Chrome/CDP, home directory, allowed tools not enabled on the workflow.
4. Prompt quality: ambiguity, missing paths, missing tool guidance, variables not filled, conflicting instructions.
5. Model behavior: unnecessary loops, ignored tool results, hallucinated paths.

## Output format (Markdown only)

Use exactly these sections:

### Summary
One short paragraph: what the run was trying to do and how it ended.

### Issues found
Bullet list. Each bullet: severity (high / medium / low), what happened, and evidence (cite message #sequence and role/tool name).

### Recommended fixes
Numbered, actionable steps the operator can take *now* (edit workflow, change Settings, fix a folder path, enable a tool, re-run with variables). Do not suggest code changes to the platform unless the transcript shows a clear product bug.

### Prompt improvements
Concrete edits to the workflow user prompt template. Include:
- What to add, remove, or clarify (quote or paraphrase the current template when helpful).
- A single fenced code block labeled `suggested_prompt_excerpt` containing copy-paste-ready text (a section to add or a full replacement template only if warranted).

## Rules

- Base every claim on the provided run context and transcript only.
- Prefer fixing the prompt and paths over blaming the model when tools returned explicit errors.
- If the run succeeded with no material issues, say so briefly and still offer 1–2 optional prompt improvements if useful.
- Be concise; avoid repeating the full transcript.
- Do not invent files, settings, or tool results not present in the input.
"""


async def _settings_dict() -> dict[str, str]:
    async with async_session() as db:
        result = await db.execute(select(AppSettings))
        return {row.key: row.value or "" for row in result.scalars().all()}


def _truncate_message_content(role: str, content: str | None) -> str:
    text = content or ""
    if role != "tool_result" or len(text) <= TOOL_RESULT_TRUNCATE:
        return text
    head = text[:TOOL_RESULT_HEAD_TAIL]
    tail = text[-TOOL_RESULT_HEAD_TAIL:]
    return f"{head}\n\n[... truncated ...]\n\n{tail}"


def _format_message_line(msg: WorkflowRunMessage) -> str:
    tool_part = f" (tool: {msg.tool_name})" if msg.tool_name else ""
    body = _truncate_message_content(msg.role, msg.content)
    return f"#{msg.sequence} [{msg.role}]{tool_part}\n{body}"


def _message_is_essential(msg: WorkflowRunMessage, *, first_user_seq: int | None, last_assistant_seq: int | None) -> bool:
    if msg.role == "system":
        return True
    if first_user_seq is not None and msg.sequence == first_user_seq:
        return True
    if last_assistant_seq is not None and msg.sequence == last_assistant_seq:
        return True
    content = (msg.content or "").lower()
    if "error" in content:
        return True
    return False


def format_transcript(messages: list[WorkflowRunMessage]) -> str:
    """Format run messages for the analyzer, with truncation to fit context limits."""
    if not messages:
        return "(empty transcript)"

    first_user_seq = next((m.sequence for m in messages if m.role == "user"), None)
    last_assistant_seq = next(
        (m.sequence for m in reversed(messages) if m.role == "assistant"), None
    )

    lines = [_format_message_line(m) for m in messages]
    combined = "\n\n".join(lines)
    if len(combined) <= MAX_TRANSCRIPT_CHARS:
        return combined

    essential = [
        m
        for m in messages
        if _message_is_essential(
            m,
            first_user_seq=first_user_seq,
            last_assistant_seq=last_assistant_seq,
        )
    ]
    middle = [m for m in messages if m not in essential]
    result_parts = [_format_message_line(m) for m in essential]
    omitted = len(middle)
    if omitted:
        result_parts.append(
            f"\n[... {omitted} middle message(s) omitted for length; "
            "essential messages and errors retained ...]\n"
        )
    combined = "\n\n".join(result_parts)
    if len(combined) > MAX_TRANSCRIPT_CHARS:
        combined = combined[:MAX_TRANSCRIPT_CHARS] + "\n\n[... transcript truncated ...]"
    return combined


def build_analysis_user_message(
    run: WorkflowRun,
    workflow: WorkflowDefinition,
    playbook: PlaybookSettings | None,
    messages: list[WorkflowRunMessage],
) -> str:
    allowed_tools = json.loads(workflow.allowed_tools_json or "[]")
    variables = json.loads(run.variables_json or "{}")
    system_prompt = playbook.system_prompt if playbook else ""

    started = run.started_at.strftime("%Y-%m-%d %H:%M UTC") if run.started_at else "—"
    ended = run.ended_at.strftime("%Y-%m-%d %H:%M UTC") if run.ended_at else "—"
    run_error = run.error or "(none)"

    metadata = f"""## Run metadata
- Run ID: {run.id}
- Status: {run.status}
- Provider / model: {run.provider} / {run.model}
- Started: {started}
- Ended: {ended}
- Run error: {run_error}
- Workflow name: {workflow.name} (workflow_id={workflow.id})
- Runtime Algorithm: {workflow.playbook_name}
- Allowed tools: {", ".join(allowed_tools) if allowed_tools else "(none)"}
- Run variables: {json.dumps(variables, indent=2)}
- App home directory: {settings.home_dir}
- Edit workflow: /workflows/{workflow.id}/edit
"""

    definition = f"""## Workflow definition
### user_prompt_template
{workflow.user_prompt_template}

### Runtime Algorithm system_prompt
{system_prompt or "(empty)"}
"""

    transcript = f"""## Chat transcript
{format_transcript(messages)}
"""
    return f"{metadata}\n{definition}\n{transcript}"


async def analyze_run(run_id: int) -> str:
    """Analyze a finished workflow run and return markdown suggestions."""
    async with async_session() as db:
        run = await db.get(WorkflowRun, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        if run.status == "running":
            raise ValueError("Cannot analyze a run that is still in progress.")

        workflow = await db.get(WorkflowDefinition, run.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {run.workflow_id} not found for this run.")

        playbook_result = await db.execute(
            select(PlaybookSettings).where(
                PlaybookSettings.playbook_name == workflow.playbook_name
            )
        )
        playbook = playbook_result.scalar_one_or_none()

        message_result = await db.execute(
            select(WorkflowRunMessage)
            .where(WorkflowRunMessage.run_id == run_id)
            .order_by(WorkflowRunMessage.sequence)
        )
        messages = list(message_result.scalars().all())

    if not messages:
        return (
            "### Summary\n"
            "This run has no persisted messages to analyze.\n\n"
            "### Recommended fixes\n"
            "1. Re-run the workflow and check that the default provider API key is configured under Settings."
        )

    app_settings = await _settings_dict()
    provider_name = (app_settings.get("default_provider") or "openai").strip() or "openai"
    model = (app_settings.get("default_model") or "gpt-5.5").strip() or "gpt-5.5"

    user_content = build_analysis_user_message(run, workflow, playbook, messages)
    llm_messages = [
        {"role": "system", "content": RUN_FIX_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    async def _noop_on_message(_msg: dict[str, Any]) -> None:
        return None

    async def _noop_tool_executor(_name: str, _args: dict) -> str:
        return ""

    provider = get_provider(provider_name, app_settings)
    result = await provider.run_thread(
        messages=llm_messages,
        model=model,
        tools=[],
        tool_executor=_noop_tool_executor,
        on_message=_noop_on_message,
    )
    content = (result or {}).get("content", "").strip()
    if not content:
        raise RuntimeError("The analysis model returned an empty response.")
    return content
