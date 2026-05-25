"""Workflow routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.main import get_templates
from app.models import WorkflowDefinition
from app.seed.sample_workflows import (
    ensure_sample_workflows,
    get_sample_manifest,
    missing_sample_slugs,
)
from app.routers.playbooks import PLAYBOOK_NAMES
from app.services.ai.tools import TOOL_DEFINITIONS
from app.services.mcp import AGENTIC_TOOL_NAMES, zapier_mcp_configured
from app.services.mcp.zapier import is_zapier_mcp_tool
from app.services.workflow_prompts import extract_user_prompt_variables
from app.services.workflow_runner import (
    create_and_start_workflow_run,
    delete_workflow_runs_for_workflow,
)

router = APIRouter(tags=["workflows"])


def _tool_names() -> list[str]:
    return [tool["function"]["name"] for tool in TOOL_DEFINITIONS]


def _normalize_playbook_name(playbook_name: str | None) -> str:
    if playbook_name in PLAYBOOK_NAMES:
        return playbook_name
    return PLAYBOOK_NAMES[0]


def _all_selectable_tool_names() -> list[str]:
    return _tool_names() + list(AGENTIC_TOOL_NAMES)


def _clean_allowed_tools(allowed_tools: list[str]) -> list[str]:
    available = set(_all_selectable_tool_names())
    return [tool for tool in allowed_tools if tool in available]


def _sort_workflows(rows: list[WorkflowDefinition]) -> list[WorkflowDefinition]:
    def by_created_desc(workflow: WorkflowDefinition) -> float:
        if workflow.created_at is None:
            return 0.0
        return -workflow.created_at.timestamp()

    samples = sorted(
        [w for w in rows if w.seed_slug],
        key=by_created_desc,
    )
    user_rows = sorted(
        [w for w in rows if not w.seed_slug],
        key=by_created_desc,
    )
    return samples + user_rows


def _workflow_list_item(workflow: WorkflowDefinition) -> dict:
    manifest = (
        get_sample_manifest(workflow.seed_slug) if workflow.seed_slug else None
    )
    return {
        "workflow": workflow,
        "variables": json.loads(workflow.user_prompt_variables_json or "[]"),
        "tools": json.loads(workflow.allowed_tools_json or "[]"),
        "is_sample": bool(workflow.seed_slug),
        "variable_defaults": manifest.variable_defaults if manifest else {},
    }


async def _workflow_form_context(
    *,
    request: Request,
    db: AsyncSession,
    title: str,
    form_action: str,
    workflow_name: str,
    selected_playbook: str,
    user_prompt_template: str,
    selected_tools: list[str],
    error: str = "",
) -> dict:
    from app.routers.settings import get_all_settings

    all_settings = await get_all_settings(db)
    zapier_ok = zapier_mcp_configured(all_settings)
    return {
        "active_page": "workflows",
        "title": title,
        "form_action": form_action,
        "workflow_name": workflow_name,
        "playbook_names": PLAYBOOK_NAMES,
        "selected_playbook": selected_playbook,
        "available_tools": _tool_names(),
        "zapier_tools": list(AGENTIC_TOOL_NAMES),
        "zapier_mcp_configured": zapier_ok,
        "selected_tools": selected_tools,
        "user_prompt_template": user_prompt_template,
        "app_home_dir": str(settings.workspace_root),
        "error": error,
    }


@router.get("/workflows", response_class=HTMLResponse)
async def workflows(
    request: Request,
    db: AsyncSession = Depends(get_db),
    seeded: str | None = None,
):
    """Render the list of workflow definitions."""
    templates = get_templates()
    result = await db.execute(select(WorkflowDefinition))
    workflow_rows = _sort_workflows(list(result.scalars().all()))
    existing_slugs = {w.seed_slug for w in workflow_rows if w.seed_slug}
    workflows_with_variables = [_workflow_list_item(w) for w in workflow_rows]
    return templates.TemplateResponse(
        request,
        "workflows.html",
        {
            "active_page": "workflows",
            "workflows": workflows_with_variables,
            "missing_sample_slugs": missing_sample_slugs(existing_slugs),
            "show_seeded_notice": seeded == "1",
            "app_home_dir": str(settings.workspace_root),
        },
    )


@router.post("/workflows/seed-samples")
async def seed_sample_workflows(db: AsyncSession = Depends(get_db)):
    """Install bundled sample workflows that are not already present."""
    await ensure_sample_workflows(db)
    return RedirectResponse("/workflows?seeded=1", status_code=303)


async def _workflow_detail_context(workflow: WorkflowDefinition) -> dict:
    manifest = (
        get_sample_manifest(workflow.seed_slug) if workflow.seed_slug else None
    )
    return {
        "active_page": "workflows",
        "workflow": workflow,
        "variables": json.loads(workflow.user_prompt_variables_json or "[]"),
        "tools": json.loads(workflow.allowed_tools_json or "[]"),
        "is_sample": bool(workflow.seed_slug),
        "quick_start": manifest.variable_defaults if manifest else None,
        "app_home_dir": str(settings.workspace_root),
    }


@router.get("/workflows/new", response_class=HTMLResponse)
async def new_workflow(request: Request, db: AsyncSession = Depends(get_db)):
    """Render the new workflow form."""
    templates = get_templates()
    return templates.TemplateResponse(
        request,
        "workflow_form.html",
        await _workflow_form_context(
            request=request,
            db=db,
            title="New Workflow",
            form_action="/workflows",
            workflow_name="",
            selected_playbook=PLAYBOOK_NAMES[0],
            user_prompt_template="",
            selected_tools=_tool_names(),
        ),
    )


@router.post("/workflows", response_class=HTMLResponse)
async def create_workflow(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(""),
    playbook_name: str = Form(""),
    user_prompt_template: str = Form(""),
    allowed_tools: list[str] = Form(default=[]),
):
    """Persist a workflow definition after validating prompt constraints."""
    templates = get_templates()
    name = name.strip()
    selected_playbook = _normalize_playbook_name(playbook_name)
    user_prompt_template = user_prompt_template.strip()
    selected_tools = _clean_allowed_tools(allowed_tools)

    error = ""
    if not name:
        error = "Workflow name is required."
    elif not user_prompt_template:
        error = "Prompt Template is required."

    if error:
        return templates.TemplateResponse(
            request,
            "workflow_form.html",
            await _workflow_form_context(
                request=request,
                db=db,
                title="New Workflow",
                form_action="/workflows",
                workflow_name=name,
                selected_playbook=selected_playbook,
                user_prompt_template=user_prompt_template,
                selected_tools=selected_tools,
                error=error,
            ),
            status_code=400,
        )

    variables = extract_user_prompt_variables(user_prompt_template)
    db.add(
        WorkflowDefinition(
            name=name,
            playbook_name=selected_playbook,
            user_prompt_template=user_prompt_template,
            user_prompt_variables_json=json.dumps(variables),
            allowed_tools_json=json.dumps(selected_tools),
        )
    )
    await db.commit()
    return RedirectResponse("/workflows", status_code=303)


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
async def workflow_detail(
    workflow_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Render full workflow details."""
    templates = get_templates()
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        return RedirectResponse("/workflows", status_code=303)

    return templates.TemplateResponse(
        request,
        "workflow_detail.html",
        await _workflow_detail_context(workflow),
    )


@router.post("/workflows/{workflow_id}/run")
async def run_workflow(workflow_id: int, request: Request):
    """Start a workflow run in the background and redirect to the run detail."""
    form = await request.form()
    variables = {
        key.removeprefix("variable__"): str(value)
        for key, value in form.multi_items()
        if key.startswith("variable__")
    }
    run_id = await create_and_start_workflow_run(workflow_id, variables)
    return RedirectResponse(f"/runs/{run_id}", status_code=303)


@router.post("/workflows/{workflow_id}/delete")
async def delete_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a workflow and any runs created from it."""
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if workflow:
        await delete_workflow_runs_for_workflow(workflow_id)
        await db.execute(delete(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id))
        await db.commit()
    return RedirectResponse("/workflows", status_code=303)


@router.get("/workflows/{workflow_id}/edit", response_class=HTMLResponse)
async def edit_workflow(
    workflow_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Render the edit workflow form."""
    templates = get_templates()
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        return RedirectResponse("/workflows", status_code=303)

    return templates.TemplateResponse(
        request,
        "workflow_form.html",
        await _workflow_form_context(
            request=request,
            db=db,
            title=f"Edit {workflow.name}",
            form_action=f"/workflows/{workflow.id}",
            workflow_name=workflow.name,
            selected_playbook=_normalize_playbook_name(workflow.playbook_name),
            user_prompt_template=workflow.user_prompt_template,
            selected_tools=json.loads(workflow.allowed_tools_json or "[]"),
        ),
    )


@router.post("/workflows/{workflow_id}", response_class=HTMLResponse)
async def update_workflow(
    workflow_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(""),
    playbook_name: str = Form(""),
    user_prompt_template: str = Form(""),
    allowed_tools: list[str] = Form(default=[]),
):
    """Update a workflow definition."""
    templates = get_templates()
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        return RedirectResponse("/workflows", status_code=303)

    name = name.strip()
    selected_playbook = _normalize_playbook_name(playbook_name)
    user_prompt_template = user_prompt_template.strip()
    selected_tools = _clean_allowed_tools(allowed_tools)

    error = ""
    if not name:
        error = "Workflow name is required."
    elif not user_prompt_template:
        error = "Prompt Template is required."

    if error:
        return templates.TemplateResponse(
            request,
            "workflow_form.html",
            await _workflow_form_context(
                request=request,
                db=db,
                title=f"Edit {workflow.name}",
                form_action=f"/workflows/{workflow.id}",
                workflow_name=name,
                selected_playbook=selected_playbook,
                user_prompt_template=user_prompt_template,
                selected_tools=selected_tools,
                error=error,
            ),
            status_code=400,
        )

    workflow.name = name
    workflow.playbook_name = selected_playbook
    workflow.user_prompt_template = user_prompt_template
    workflow.user_prompt_variables_json = json.dumps(
        extract_user_prompt_variables(user_prompt_template)
    )
    workflow.allowed_tools_json = json.dumps(selected_tools)
    await db.commit()
    return RedirectResponse("/workflows", status_code=303)
