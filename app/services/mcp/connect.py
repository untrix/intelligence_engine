"""Connection test helpers for Zapier MCP."""

from __future__ import annotations

from app.services.mcp.client import ZapierMcpSession
from app.services.mcp.config import ZapierMcpSettings
from app.services.mcp.zapier import is_agentic_mode_tool_set


async def test_zapier_mcp_connection(
    cfg: ZapierMcpSettings,
) -> tuple[bool, str, int, bool]:
    """
    Connect, list tools, and return (ok, message, tool_count, agentic_detected).
    """
    if not cfg.api_token:
        return False, "API token is required.", 0, False
    try:
        async with ZapierMcpSession(cfg.server_url, cfg.api_token) as session:
            names = session.tool_names()
            agentic = is_agentic_mode_tool_set(names)
            mode = "Agentic" if agentic else "Classic or mixed"
            return (
                True,
                f"Connected — {len(names)} tools ({mode} mode).",
                len(names),
                agentic,
            )
    except Exception as exc:
        return False, str(exc), 0, False
