"""Integrations catalog routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.main import get_templates
from app.services.ai.tools import TOOL_DEFINITIONS

router = APIRouter(tags=["integrations"])


@router.get("/integrations", response_class=HTMLResponse)
async def integrations_page(request: Request):
    """Render the read-only list of integrations available to agents."""
    templates = get_templates()
    tools = [tool["function"] for tool in TOOL_DEFINITIONS]
    return templates.TemplateResponse(
        request,
        "tools.html",
        {
            "active_page": "integrations",
            "tools": tools,
        },
    )
