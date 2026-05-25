"""Integrations catalog routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_templates
from app.routers.settings import _hx_trigger_toast, get_all_settings, save_setting
from app.services.ai.tools import TOOL_DEFINITIONS
from app.services.mcp import (
    AGENTIC_TOOL_NAMES,
    get_zapier_mcp_settings,
    normalize_zapier_credentials,
    zapier_mcp_configured,
)
from app.services.mcp.connect import test_zapier_mcp_connection
router = APIRouter(tags=["integrations"])


@router.get("/integrations", response_class=HTMLResponse)
async def integrations_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Render inbuilt tools and Zapier MCP configuration."""
    templates = get_templates()
    all_settings = await get_all_settings(db)
    zapier = get_zapier_mcp_settings(all_settings)
    tool_count_raw = all_settings.get("zapier_mcp_last_tool_count") or ""
    try:
        tool_count = int(tool_count_raw) if tool_count_raw else None
    except ValueError:
        tool_count = None
    agentic = (all_settings.get("zapier_mcp_agentic_mode") or "") == "true"
    configured = zapier_mcp_configured(all_settings)
    builtin = [tool["function"] for tool in TOOL_DEFINITIONS]
    return templates.TemplateResponse(
        request,
        "tools.html",
        {
            "active_page": "integrations",
            "tools": builtin,
            "zapier": zapier,
            "zapier_configured": configured,
            "zapier_has_token": bool(zapier.api_token),
            "zapier_tool_count": tool_count,
            "zapier_agentic": agentic,
            "agentic_tool_names": AGENTIC_TOOL_NAMES,
        },
    )


@router.post("/integrations/zapier-mcp/save", response_class=HTMLResponse)
async def save_zapier_mcp(
    db: AsyncSession = Depends(get_db),
    zapier_mcp_enabled: str = Form("false"),
    zapier_mcp_server_url: str = Form(""),
    zapier_mcp_api_token: str = Form(""),
    zapier_mcp_api_token_unchanged: str = Form(""),
):
    all_settings = await get_all_settings(db)
    if zapier_mcp_api_token_unchanged and not zapier_mcp_api_token.strip():
        token = all_settings.get("zapier_mcp_api_token") or ""
    else:
        token = zapier_mcp_api_token

    url, token = normalize_zapier_credentials(zapier_mcp_server_url, token)
    enabled = zapier_mcp_enabled.strip().lower() in ("true", "1", "on", "yes")

    for key, value in (
        ("zapier_mcp_enabled", "true" if enabled else "false"),
        ("zapier_mcp_server_url", url),
        ("zapier_mcp_api_token", token),
    ):
        await save_setting(db, key, value)
    await db.commit()
    return HTMLResponse(
        content="",
        status_code=200,
        headers=_hx_trigger_toast("Zapier MCP settings saved.", "success"),
    )


@router.post("/integrations/zapier-mcp/test", response_class=HTMLResponse)
async def test_zapier_mcp(
    db: AsyncSession = Depends(get_db),
    zapier_mcp_server_url: str = Form(""),
    zapier_mcp_api_token: str = Form(""),
    zapier_mcp_api_token_unchanged: str = Form(""),
):
    all_settings = await get_all_settings(db)
    if zapier_mcp_api_token_unchanged and not zapier_mcp_api_token.strip():
        token = all_settings.get("zapier_mcp_api_token") or ""
    else:
        token = zapier_mcp_api_token
    url, token = normalize_zapier_credentials(
        zapier_mcp_server_url or all_settings.get("zapier_mcp_server_url") or "",
        token,
    )
    cfg = get_zapier_mcp_settings(
        {
            **all_settings,
            "zapier_mcp_server_url": url,
            "zapier_mcp_api_token": token,
            "zapier_mcp_enabled": "true",
        }
    )
    ok, message, count, agentic = await test_zapier_mcp_connection(cfg)
    if ok:
        await save_setting(db, "zapier_mcp_last_tool_count", str(count))
        await save_setting(
            db, "zapier_mcp_agentic_mode", "true" if agentic else "false"
        )
        if not (all_settings.get("zapier_mcp_api_token") or "").strip() and token:
            await save_setting(db, "zapier_mcp_api_token", token)
        if url:
            await save_setting(db, "zapier_mcp_server_url", url)
        await db.commit()
    toast_type = "success" if ok else "danger"
    return HTMLResponse(
        content="",
        status_code=200,
        headers=_hx_trigger_toast(message, toast_type),
    )
