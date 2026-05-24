"""Workflow routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_templates
from app.models import WorkflowDefinition
from app.routers.playbooks import PLAYBOOK_NAMES
from app.services.ai.tools import TOOL_DEFINITIONS
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


def _clean_allowed_tools(allowed_tools: list[str]) -> list[str]:
    available_tools = _tool_names()
    return [tool for tool in allowed_tools if tool in available_tools]


def _workflow_form_context(
    *,
    request: Request,
    title: str,
    form_action: str,
    workflow_name: str,
    selected_playbook: str,
    user_prompt_template: str,
    selected_tools: list[str],
    error: str = "",
) -> dict:
    return {
        "active_page": "workflows",
        "title": title,
        "form_action": form_action,
        "workflow_name": workflow_name,
        "playbook_names": PLAYBOOK_NAMES,
        "selected_playbook": selected_playbook,
        "available_tools": _tool_names(),
        "selected_tools": selected_tools,
        "user_prompt_template": user_prompt_template,
        "error": error,
    }


@router.get("/workflows", response_class=HTMLResponse)
async def workflows(request: Request, db: AsyncSession = Depends(get_db)):
    """Render the list of workflow definitions."""
    templates = get_templates()
    result = await db.execute(
        select(WorkflowDefinition).order_by(WorkflowDefinition.created_at.desc())
    )
    workflow_rows = result.scalars().all()
    workflows_with_variables = [
        {
            "workflow": workflow,
            "variables": json.loads(workflow.user_prompt_variables_json or "[]"),
            "tools": json.loads(workflow.allowed_tools_json or "[]"),
        }
        for workflow in workflow_rows
    ]
    return templates.TemplateResponse(
        request,
        "workflows.html",
        {
            "active_page": "workflows",
            "workflows": workflows_with_variables,
        },
    )


async def _workflow_detail_context(workflow: WorkflowDefinition) -> dict:
    return {
        "active_page": "workflows",
        "workflow": workflow,
        "variables": json.loads(workflow.user_prompt_variables_json or "[]"),
        "tools": json.loads(workflow.allowed_tools_json or "[]"),
    }


@router.get("/workflows/new", response_class=HTMLResponse)
async def new_workflow(request: Request):
    """Render the new workflow form."""
    templates = get_templates()
    return templates.TemplateResponse(
        request,
        "workflow_form.html",
        _workflow_form_context(
            request=request,
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
            _workflow_form_context(
                request=request,
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
        _workflow_form_context(
            request=request,
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
            _workflow_form_context(
                request=request,
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
