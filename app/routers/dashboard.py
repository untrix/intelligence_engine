"""Root redirect and shutdown route."""

import json
import logging
import os
import signal

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=RedirectResponse)
async def root():
    """Send users to the primary Workflows page."""
    return RedirectResponse("/workflows", status_code=303)


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
