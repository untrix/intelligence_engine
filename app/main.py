"""FastAPI application entry point, router registration, and startup seeding."""

import glob
import logging
import os
import shutil
import signal
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import markdown
from fastapi import FastAPI, Request
from markupsafe import Markup
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
from app.services.browser import BROWSER_TEMP_PREFIX

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.getLogger("app").setLevel(logging.INFO)
    root = logging.getLogger()
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)


def _cleanup_stale_browser_temps():
    """Remove leftover browser temp dirs from previous runs."""
    pattern = Path(tempfile.gettempdir()) / f"{BROWSER_TEMP_PREFIX}*"
    for d in glob.glob(str(pattern)):
        try:
            shutil.rmtree(d, ignore_errors=True)
            logger.info("Cleaned up stale temp browser profile: %s", d)
        except Exception:
            logger.warning("Could not remove stale temp dir: %s", d)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    _cleanup_stale_browser_temps()
    await init_db()
    from app.services.workflow_runner import mark_stale_running_runs

    await mark_stale_running_runs()
    await _seed_defaults()
    await _seed_sample_workflows()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _render_markdown(text: str | None) -> Markup:
    if not text:
        return Markup("")
    return Markup(
        markdown.markdown(
            text,
            extensions=["extra", "nl2br", "sane_lists"],
            output_format="html",
        )
    )


templates.env.filters["markdown"] = _render_markdown


def get_templates() -> Jinja2Templates:
    return templates


from app.routers import dashboard, playbooks, runs, settings as settings_router, tools, workflows  # noqa: E402

app.include_router(dashboard.router)
app.include_router(settings_router.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(tools.router)
app.include_router(playbooks.router)


async def _seed_defaults():
    from app.database import async_session
    from app.models import AppSettings
    from sqlalchemy import select

    defaults = {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "default_concurrency": "5",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "google_api_key": "",
        "aws_profile": "",
        "aws_region": "us-east-1",
        "chrome_cdp_url": "http://127.0.0.1:9222",
        "zapier_mcp_enabled": "false",
        "zapier_mcp_server_url": "",
        "zapier_mcp_api_token": "",
    }
    async with async_session() as session:
        for key, value in defaults.items():
            result = await session.execute(
                select(AppSettings).where(AppSettings.key == key)
            )
            if not result.scalar_one_or_none():
                session.add(AppSettings(key=key, value=value))
        await session.commit()


async def _seed_sample_workflows():
    from app.database import async_session
    from app.seed.sample_workflows import ensure_sample_workflows

    async with async_session() as session:
        installed = await ensure_sample_workflows(session)
        if installed:
            logger.info("Installed sample workflows: %s", ", ".join(installed))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
