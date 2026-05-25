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

from app.config import settings

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 50_000
_READABLE_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".json", ".csv", ".html", ".xml"}
_UNREADABLE_SUFFIXES = {".gdoc", ".gsheet", ".gslides"}

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
            "name": "list_local_folder",
            "description": (
                "List the contents of a local directory. Returns readable files, "
                "other files, subfolders, and Google Docs shortcuts (.gdoc) that "
                "cannot be read. Use when the prompt gives a folder path and you "
                "only need to see what is inside before reading. Paths relative "
                "to the app home directory are accepted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The local directory path to list",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_folder",
            "description": (
                "Read all supported files in a local directory (one level, not "
                "recursive) and return their text content. Use when the prompt "
                "gives a folder path such as job files or candidate documents. "
                "Supports text files, PDF, and DOCX. Paths relative to the app "
                "home directory are accepted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The local directory path to read",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_path",
            "description": (
                "Read a local path whether it is a single file or a directory. "
                "If the path is a file, returns that file's content. If it is a "
                "directory, reads all supported files inside (same as "
                "read_local_folder). Use when the prompt does not say whether "
                "the path is a file or folder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "A local file or directory path",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": (
                "Read a single local file and return its text content. "
                "Supports text files, PDF, and DOCX. The path must be a file "
                "(include the extension). For a folder path, use "
                "read_local_folder or list_local_folder instead."
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


def create_tool_executor(
    browser_context=None,
    zapier_session=None,
) -> ToolExecutor:
    """Build a tool executor closure for builtin and optional Zapier MCP tools."""

    async def _execute(tool_name: str, arguments: dict) -> str:
        if zapier_session is not None:
            from app.services.mcp.zapier import is_zapier_mcp_tool

            if is_zapier_mcp_tool(tool_name):
                return await zapier_session.call_tool(tool_name, arguments)

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
        if tool_name == "list_local_folder":
            path = arguments.get("path")
            if not path:
                return "Error: missing required argument 'path'"
            return await _list_local_folder(path)
        if tool_name == "read_local_folder":
            path = arguments.get("path")
            if not path:
                return "Error: missing required argument 'path'"
            return await _read_local_folder(path)
        if tool_name == "read_local_path":
            path = arguments.get("path")
            if not path:
                return "Error: missing required argument 'path'"
            return await _read_local_path(path)
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
            "Configure Chrome remote debugging in Settings (CDP URL) "
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


def _resolve_local_path(path: str) -> Path:
    """Expand user/home-relative paths against the configured app home directory."""
    raw = (path or "").strip()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (settings.home_dir / p).resolve()
    else:
        p = p.resolve()
    return p


def _classify_directory_children(directory: Path) -> tuple[list[Path], list[Path], list[Path], list[Path]]:
    """Return (subdirs, readable_files, shortcuts, other_files)."""
    subdirs: list[Path] = []
    readable: list[Path] = []
    shortcuts: list[Path] = []
    other: list[Path] = []
    for child in sorted(directory.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir():
            subdirs.append(child)
            continue
        if not child.is_file():
            continue
        suffix = child.suffix.lower()
        if suffix in _UNREADABLE_SUFFIXES:
            shortcuts.append(child)
        elif suffix in _READABLE_SUFFIXES or suffix == "":
            readable.append(child)
        else:
            other.append(child)
    return subdirs, readable, shortcuts, other


def _format_folder_listing(directory: Path) -> str:
    subdirs, readable, shortcuts, other = _classify_directory_children(directory)
    lines = [f"Contents of {directory}:"]

    if subdirs:
        lines.append("\nSubdirectories:")
        for child in subdirs:
            lines.append(f"- {child}/")

    if readable:
        lines.append("\nReadable files:")
        for child in readable:
            lines.append(f"- {child}")
    else:
        lines.append("\nReadable files: (none)")

    if shortcuts:
        lines.append(
            "\nGoogle Docs/Sheets shortcuts (not readable; export to .docx/.pdf):"
        )
        for child in shortcuts:
            lines.append(f"- {child}")

    if other:
        lines.append("\nOther files:")
        for child in other[:20]:
            lines.append(f"- {child}")

    return "\n".join(lines)


def _directory_not_file_message(directory: Path) -> str:
    return (
        f"'{directory}' is a directory, not a file. "
        "Use read_local_folder to read all supported files in the folder, "
        "or list_local_folder to list contents only."
    )


def _not_a_directory_message(path: Path) -> str:
    return (
        f"'{path}' is a file, not a directory. "
        "Use read_local_file or read_local_path to read it."
    )


def _suggest_similar_files(missing: Path) -> str:
    parent = missing.parent
    if not parent.is_dir():
        return f"File not found: {missing}"

    name = missing.name.lower()
    tokens = [t for t in name.replace("_", " ").replace("-", " ").split() if len(t) > 2]
    candidates: list[Path] = []
    for child in sorted(parent.iterdir()):
        if not child.is_file() or child.name.startswith("."):
            continue
        if child.suffix.lower() in _UNREADABLE_SUFFIXES:
            continue
        child_name = child.name.lower()
        if any(token in child_name for token in tokens):
            candidates.append(child)

    lines = [f"File not found: {missing}"]
    if parent.is_dir():
        doc_like = [
            c
            for c in sorted(parent.iterdir())
            if c.is_file()
            and not c.name.startswith(".")
            and c.suffix.lower() in _READABLE_SUFFIXES
        ]
        if candidates:
            lines.append("\nDid you mean one of these?")
            for child in candidates[:10]:
                lines.append(f"- {child}")
        elif doc_like:
            lines.append(f"\nFiles in {parent}:")
            for child in doc_like[:15]:
                lines.append(f"- {child}")
    lines.append(
        "\nUse read_local_folder for a directory path or read_local_file for a single file."
    )
    return "\n".join(lines)


def _read_file_bytes(p: Path) -> str:
    suffix = p.suffix.lower()

    if suffix in _UNREADABLE_SUFFIXES:
        return (
            f"Cannot read Google Docs shortcut file: {p}\n"
            "Export the document to .docx or .pdf on disk and use that path."
        )

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


async def _list_local_folder(path: str) -> str:
    try:
        p = _resolve_local_path(path)
        if not p.exists():
            return _suggest_similar_files(p)
        if not p.is_dir():
            return _not_a_directory_message(p)
        return _format_folder_listing(p)
    except PermissionError:
        return f"Error listing folder {path}: Permission denied"
    except Exception as e:
        return f"Error listing folder {path}: {str(e)}"


async def _read_local_folder(path: str) -> str:
    try:
        p = _resolve_local_path(path)
        if not p.exists():
            return _suggest_similar_files(p)
        if not p.is_dir():
            return _not_a_directory_message(p)

        _subdirs, readable, shortcuts, other = _classify_directory_children(p)
        if not readable:
            parts = [f"No readable files in {p}."]
            listing = _format_folder_listing(p)
            if shortcuts or other or _subdirs:
                parts.append(listing)
            return "\n\n".join(parts)

        sections: list[str] = [f"Contents of folder {p} ({len(readable)} file(s)):\n"]
        for child in readable:
            try:
                body = _read_file_bytes(child)
            except PermissionError:
                body = "Error: Permission denied"
            except Exception as e:
                body = f"Error: {e}"
            sections.append(f"=== {child.name} ===\n{body}")

        combined = "\n\n".join(sections)
        return _truncate(combined)
    except PermissionError:
        return f"Error reading folder {path}: Permission denied"
    except Exception as e:
        return f"Error reading folder {path}: {str(e)}"


async def _read_local_path(path: str) -> str:
    try:
        p = _resolve_local_path(path)
        if not p.exists():
            return _suggest_similar_files(p)
        if p.is_dir():
            return await _read_local_folder(path)
        return _read_file_bytes(p)
    except PermissionError:
        return f"Error reading path {path}: Permission denied"
    except Exception as e:
        return f"Error reading path {path}: {str(e)}"


async def _read_local_file(path: str) -> str:
    try:
        p = _resolve_local_path(path)
        if not p.exists():
            return _suggest_similar_files(p)
        if p.is_dir():
            return _directory_not_file_message(p)
        return _read_file_bytes(p)
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
