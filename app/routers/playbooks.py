"""Agent Runtime catalog routes.

The persisted table/column names still use "playbook" for database compatibility.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_templates
from app.models import PlaybookSettings

router = APIRouter(tags=["playbooks"])

PLAYBOOK_NAMES = [
    "Single Turn",
    "ReAct",
    "Tree of Thoughts",
    "Reflexion",
    "MCTS / LATS",
    "Autonomous Group",
    "Orchestrated Group",
]


def _normalize_playbook_name(playbook_name: str | None) -> str:
    if playbook_name in PLAYBOOK_NAMES:
        return playbook_name
    return PLAYBOOK_NAMES[0]


async def _get_settings(
    db: AsyncSession, playbook_name: str
) -> PlaybookSettings | None:
    result = await db.execute(
        select(PlaybookSettings).where(PlaybookSettings.playbook_name == playbook_name)
    )
    return result.scalar_one_or_none()


@router.get("/agent-runtime", response_class=HTMLResponse)
@router.get("/playbooks", response_class=HTMLResponse)
async def playbooks_page(
    request: Request,
    runtime: str | None = None,
    playbook: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Render settings for the selected Runtime Algorithm."""
    templates = get_templates()
    selected_playbook = _normalize_playbook_name(runtime or playbook)
    setting = await _get_settings(db, selected_playbook)
    return templates.TemplateResponse(
        request,
        "playbooks.html",
        {
            "active_page": "playbooks",
            "playbook_names": PLAYBOOK_NAMES,
            "selected_playbook": selected_playbook,
            "system_prompt": setting.system_prompt if setting else "",
        },
    )
