"""Zapier MCP client session using Streamable HTTP."""

from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from datetime import timedelta

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent, Tool

from app.services.mcp.schemas import mcp_tools_to_openai

logger = logging.getLogger(__name__)


def _format_tool_result(result: CallToolResult) -> str:
    if result.isError:
        parts = []
        for block in result.content:
            if isinstance(block, TextContent):
                parts.append(block.text)
            else:
                parts.append(str(block))
        return "Error: " + ("\n".join(parts) if parts else "tool returned an error")

    parts: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent):
            parts.append(block.text)
        else:
            parts.append(str(block))
    if result.structuredContent:
        parts.append(json.dumps(result.structuredContent, indent=2))
    return "\n".join(parts) if parts else "(empty result)"


class ZapierMcpSession:
    """Per-run MCP session to Zapier (Streamable HTTP + Bearer token)."""

    def __init__(self, server_url: str, api_token: str) -> None:
        self.server_url = server_url
        self.api_token = api_token
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tools: list[Tool] = []

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("Zapier MCP session is not open")
        return self._session

    async def __aenter__(self) -> ZapierMcpSession:
        self._stack = AsyncExitStack()
        http_client = await self._stack.enter_async_context(
            httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Accept": "application/json, text/event-stream",
                },
                timeout=httpx.Timeout(60.0, read=300.0),
            )
        )
        read_stream, write_stream, _ = await self._stack.enter_async_context(
            streamable_http_client(
                self.server_url,
                http_client=http_client,
                terminate_on_close=True,
            )
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        listed = await self._session.list_tools()
        self._tools = list(listed.tools)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self._session = None
        self._tools = []

    def tool_names(self) -> list[str]:
        return [t.name for t in self._tools]

    def openai_tools(self, allowed_names: set[str] | None = None) -> list[dict]:
        tools = self._tools
        if allowed_names is not None:
            tools = [t for t in tools if t.name in allowed_names]
        return mcp_tools_to_openai(tools)

    async def call_tool(self, name: str, arguments: dict | None = None) -> str:
        logger.info("Zapier MCP tool call: %s", name)
        result = await self.session.call_tool(
            name,
            arguments or {},
            read_timeout_seconds=timedelta(minutes=5),
        )
        return _format_tool_result(result)

    async def fetch_enabled_actions_context(self) -> str | None:
        """Call list_enabled_zapier_actions for system-prompt bootstrap."""
        if not any(t.name == "list_enabled_zapier_actions" for t in self._tools):
            return None
        try:
            body = await self.call_tool("list_enabled_zapier_actions", {})
            return (
                "Zapier MCP — currently enabled actions (from server):\n"
                f"{body}"
            )
        except Exception:
            logger.exception("Failed to bootstrap list_enabled_zapier_actions")
            return None
