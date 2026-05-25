"""Convert MCP tool definitions to OpenAI function-calling shape."""

from __future__ import annotations

from typing import Any

from mcp.types import Tool


def mcp_tool_to_openai(tool: Tool) -> dict[str, Any]:
    """Map an MCP Tool to the structure used by Intelligence Engine providers."""
    schema = tool.inputSchema or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }


def mcp_tools_to_openai(tools: list[Tool]) -> list[dict[str, Any]]:
    return [mcp_tool_to_openai(t) for t in tools]
