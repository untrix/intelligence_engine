"""
Agent tool definitions and execution.

Tools that the AI model can call via function calling.
The app executes these on behalf of the agent.
"""

import asyncio
import io
import logging
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from ddgs import DDGS
from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 50_000

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch the content of a URL using a lightweight HTTP client. "
                "Best for direct file downloads (PDFs, DOCX), APIs, and simple "
                "static web pages. Does NOT render JavaScript."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_page",
            "description": (
                "Browse a web page using a real browser with full JavaScript "
                "rendering. Use this for sites that require authentication "
                "(LinkedIn, Google Workspace) or render content via JavaScript. "
                "Returns the page text content and a list of links found on the page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to browse",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": (
                "Read a local file and return its text content. "
                "Supports text files, PDF, and DOCX."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The local file path to read",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web using DuckDuckGo and return a list of results. "
                "Use when you need to find information without a direct URL. "
                "Returns titles, URLs, and text snippets for each result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5, max 20)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


ToolExecutor = Callable[[str, dict], Awaitable[str]]


def create_tool_executor(browser_context=None) -> ToolExecutor:
    """Build a tool executor closure, optionally wired to a Playwright browser context."""

    async def _execute(tool_name: str, arguments: dict) -> str:
        if tool_name == "fetch_url":
            url = arguments.get("url")
            if not url:
                return "Error: missing required argument 'url'"
            return await _fetch_url(url)
        if tool_name == "browse_page":
            url = arguments.get("url")
            if not url:
                return "Error: missing required argument 'url'"
            return await _browse_page(browser_context, url)
        if tool_name == "read_local_file":
            path = arguments.get("path")
            if not path:
                return "Error: missing required argument 'path'"
            return await _read_local_file(path)
        if tool_name == "web_search":
            query = arguments.get("query")
            if not query:
                return "Error: missing required argument 'query'"
            max_results = min(int(arguments.get("max_results", 5)), 20)
            return await _web_search(query, max_results)
        return f"Unknown tool: {tool_name}"

    return _execute


async def execute_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool call without browser context (legacy entry point)."""
    executor = create_tool_executor(browser_context=None)
    return await executor(tool_name, arguments)


def _truncate(text: str, max_len: int = MAX_CONTENT_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n\n[... content truncated ...]"


async def _browse_page(browser_context, url: str) -> str:
    if browser_context is None:
        return (
            "Error: Web browsing is not available. "
            "Configure Chrome in Settings (remote debugging URL or profile path) "
            "to enable browse_page."
        )
    from app.services.browser import browse_page

    return await browse_page(browser_context, url)


async def _fetch_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()

            if "pdf" in content_type:
                reader = PdfReader(io.BytesIO(response.content))
                text_parts = []
                for page in reader.pages:
                    try:
                        extracted = page.extract_text()
                        text_parts.append(extracted or "")
                    except Exception:
                        text_parts.append("")
                return _truncate("\n".join(text_parts))

            return _truncate(response.text)
    except httpx.HTTPStatusError as e:
        return f"Error fetching URL {url}: HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        return f"Error fetching URL {url}: {str(e)}"
    except Exception as e:
        return f"Error fetching URL {url}: {str(e)}"


async def _read_local_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"File not found: {path}"
        if not p.is_file():
            return f"Not a file: {path}"

        suffix = p.suffix.lower()

        if suffix == ".pdf":
            reader = PdfReader(str(p))
            text_parts = []
            for page in reader.pages:
                try:
                    extracted = page.extract_text()
                    text_parts.append(extracted or "")
                except Exception:
                    text_parts.append("")
            return _truncate("\n".join(text_parts))

        if suffix == ".docx":
            doc = Document(str(p))
            text = "\n".join(para.text for para in doc.paragraphs)
            return _truncate(text)

        return _truncate(p.read_text(errors="replace"))
    except PermissionError:
        return f"Error reading file {path}: Permission denied"
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"


async def _web_search(query: str, max_results: int = 5) -> str:
    try:
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, lambda: DDGS().text(query, max_results=max_results)
        )

        if not results:
            return f"No results found for: {query}"

        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"{i}. {r['title']}\n"
                f"   URL: {r['href']}\n"
                f"   {r['body']}"
            )
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning("web_search failed for %r: %s", query, e)
        return f"Error performing web search: {str(e)}"
