"""Zapier MCP (Agentic mode) constants and helpers."""

from __future__ import annotations

# Stable Agentic meta-tools (Zapier MCP). Used for workflow allowlist UI and routing.
AGENTIC_TOOL_NAMES: tuple[str, ...] = (
    "list_enabled_zapier_actions",
    "discover_zapier_actions",
    "enable_zapier_action",
    "disable_zapier_action",
    "auto_provision_mcp",
    "execute_zapier_read_action",
    "execute_zapier_write_action",
    "get_configuration_url",
    "list_zapier_skills",
    "get_zapier_skill",
    "create_zapier_skill",
    "update_zapier_skill",
    "delete_zapier_skill",
    "send_feedback",
)

_AGENTIC_SET = frozenset(AGENTIC_TOOL_NAMES)


def is_zapier_mcp_tool(name: str) -> bool:
    """Return True if the tool name is a known Zapier Agentic MCP meta-tool."""
    return name in _AGENTIC_SET


def is_agentic_mode_tool_set(tool_names: list[str]) -> bool:
    """Heuristic: server exposes Agentic meta-tools if discover is in the list."""
    return "discover_zapier_actions" in tool_names
