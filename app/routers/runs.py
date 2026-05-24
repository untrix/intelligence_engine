"""Workflow run routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_templates
from app.models import WorkflowRun, WorkflowRunMessage
from app.services.workflow_runner import delete_workflow_run, resume_workflow_run

router = APIRouter(prefix="/runs", tags=["runs"])


async def _messages_for_run(db: AsyncSession, run_id: int) -> list[WorkflowRunMessage]:
    result = await db.execute(
        select(WorkflowRunMessage)
        .where(WorkflowRunMessage.run_id == run_id)
        .order_by(WorkflowRunMessage.sequence)
    )
    return list(result.scalars().all())


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def runs_list(request: Request, db: AsyncSession = Depends(get_db)):
    """List ongoing and historical workflow runs."""
    templates = get_templates()
    result = await db.execute(
        select(WorkflowRun).order_by(WorkflowRun.started_at.desc())
    )
    return templates.TemplateResponse(
        request,
        "runs.html",
        {
            "active_page": "runs",
            "runs": result.scalars().all(),
        },
    )


@router.get("/{run_id:int}", response_class=HTMLResponse)
async def run_detail(
    request: Request,
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Render a workflow run chat."""
    templates = get_templates()
    run = await db.get(WorkflowRun, run_id)
    if not run:
        return HTMLResponse("<h3>Run not found</h3>", status_code=404)
    messages = await _messages_for_run(db, run_id)
    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {
            "active_page": "runs",
            "run": run,
            "messages": messages,
        },
    )


@router.get("/{run_id:int}/messages", response_class=HTMLResponse)
async def run_messages(
    request: Request,
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """HTMX partial returning the latest run messages."""
    templates = get_templates()
    run = await db.get(WorkflowRun, run_id)
    if not run:
        return HTMLResponse("", status_code=404)
    messages = await _messages_for_run(db, run_id)
    return templates.TemplateResponse(
        request,
        "runs/_messages.html",
        {
            "run": run,
            "messages": messages,
        },
    )


@router.post("/{run_id:int}/resume")
async def resume_run(run_id: int, user_message: str = Form(...)):
    """Append a new user message and resume a terminal workflow run."""
    await resume_workflow_run(run_id, user_message)
    return RedirectResponse(f"/runs/{run_id}", status_code=303)


@router.post("/{run_id:int}/delete")
async def delete_run(run_id: int):
    """Delete a workflow run and its chat messages."""
    await delete_workflow_run(run_id)
    return RedirectResponse("/runs", status_code=303)
