"""Read and normalize Zapier MCP settings from AppSettings dicts."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

DEFAULT_ZAPIER_MCP_URL = "https://mcp.zapier.com/api/v1/connect"


@dataclass(frozen=True)
class ZapierMcpSettings:
    enabled: bool
    server_url: str
    api_token: str


def normalize_zapier_credentials(
    server_url: str, api_token: str
) -> tuple[str, str]:
    """Strip token from URL query; return clean URL and token separately."""
    url = (server_url or "").strip() or DEFAULT_ZAPIER_MCP_URL
    token = (api_token or "").strip()

    parsed = urlparse(url)
    if parsed.query:
        query = parse_qs(parsed.query, keep_blank_values=True)
        if "token" in query:
            if not token and query["token"]:
                token = query["token"][0]
            query.pop("token", None)
            new_query = urlencode({k: v[0] for k, v in query.items()})
            url = urlunparse(parsed._replace(query=new_query))

    base = url.rstrip("/")
    if not base.endswith("/connect"):
        if "/api/v1/connect" not in base:
            base = DEFAULT_ZAPIER_MCP_URL
    return base, token


def get_zapier_mcp_settings(settings: dict[str, str]) -> ZapierMcpSettings:
    enabled = (settings.get("zapier_mcp_enabled") or "").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    url, token = normalize_zapier_credentials(
        settings.get("zapier_mcp_server_url") or "",
        settings.get("zapier_mcp_api_token") or "",
    )
    return ZapierMcpSettings(enabled=enabled, server_url=url, api_token=token)


def zapier_mcp_configured(settings: dict[str, str]) -> bool:
    cfg = get_zapier_mcp_settings(settings)
    return cfg.enabled and bool(cfg.api_token)
