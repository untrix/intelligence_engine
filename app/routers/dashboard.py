"""Dashboard route showing platform readiness."""

import json
import logging
import os
import signal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.main import get_templates
from app.models import AppSettings
from app.services.ai.registry import get_available_providers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


async def _load_settings(db: AsyncSession) -> dict:
    result = await db.execute(select(AppSettings))
    return {row.key: row.value for row in result.scalars().all()}


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    templates = get_templates()
    all_settings = await _load_settings(db)
    providers = get_available_providers(all_settings)
    chrome_configured = bool(
        (all_settings.get("chrome_cdp_url") or "").strip()
        or (all_settings.get("chrome_profile_path") or "").strip()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "settings_count": (
                await db.execute(select(func.count()).select_from(AppSettings))
            ).scalar()
            or 0,
            "providers_configured": providers,
            "chrome_configured": chrome_configured,
            "data_dir": str(settings.data_dir),
            "python_version": "3.13",
        },
    )


@router.post("/shutdown", response_class=HTMLResponse)
async def shutdown():
    """Gracefully shut down the server and its reloader (if any)."""
    pid = os.getpid()
    logger.info("Shutdown requested via UI — pid=%d", pid)
    try:
        os.killpg(os.getpgid(pid), signal.SIGINT)
    except ProcessLookupError:
        os.kill(pid, signal.SIGINT)
    return HTMLResponse(
        "",
        headers={
            "HX-Trigger": json.dumps(
                {"showToast": {"message": "Server shutting down...", "type": "info"}}
            )
        },
    )
