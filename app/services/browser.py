"""
Playwright-based browser service for rendering JS-heavy and authenticated pages.

Production path: attach to Chrome via remote debugging (CDP) — see Settings and
``make chrome-debug``.

Copied-profile helpers below (_copy_profile_to_temp, _launch_persistent_copy) are
intentionally retained but not wired from Settings or workflow runs; they may be
re-enabled later. Do not fall back to them when CDP is unset or fails.
"""

import logging
import os
import shutil
import tempfile
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 80_000
MAX_LINKS = 200
BROWSER_TEMP_PREFIX = "intelligence-engine-browser-"

# --- Copied-profile mode (retained, not used from Settings / workflow runs) ---

_PROFILE_ESSENTIALS = [
    "Cookies",
    "Cookies-journal",
    "Cookies-wal",
    "Cookies-shm",
    "Local Storage",
    "Session Storage",
    "IndexedDB",
    "Network",
    "Preferences",
    "Secure Preferences",
    "Web Data",
    "Web Data-journal",
    "Web Data-wal",
    "Web Data-shm",
    "Login Data",
    "Login Data-journal",
    "Login Data-wal",
    "Login Data-shm",
]


def _copy_profile_to_temp(
    chrome_profile_path: str,
    chrome_profile_name: str = "Default",
) -> str:
    """Copied-profile mode (unused at runtime): copy auth-essential files to a temp dir."""
    tmp = tempfile.mkdtemp(prefix=BROWSER_TEMP_PREFIX)

    local_state = os.path.join(chrome_profile_path, "Local State")
    if os.path.isfile(local_state):
        shutil.copy2(local_state, os.path.join(tmp, "Local State"))

    src_profile = os.path.join(chrome_profile_path, chrome_profile_name)
    dst_profile = os.path.join(tmp, chrome_profile_name)
    os.makedirs(dst_profile, exist_ok=True)

    copied_count = 0
    for name in _PROFILE_ESSENTIALS:
        src = os.path.join(src_profile, name)
        dst = os.path.join(dst_profile, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            copied_count += 1
        elif os.path.isfile(src):
            shutil.copy2(src, dst)
            copied_count += 1

    if copied_count == 0:
        logger.warning(
            "No profile data copied from %s — folder missing or empty? "
            "Check Chrome profile name (e.g. Profile 4) under User Data.",
            src_profile,
        )

    logger.info(
        "Copied Chrome profile essentials to temp dir %s (%s -> %s, %d entries)",
        tmp,
        chrome_profile_name,
        dst_profile,
        copied_count,
    )
    logger.warning(
        "browse_page: Chrome profile copied to temp dir %s (profile=%s, %d entries)",
        tmp,
        chrome_profile_name,
        copied_count,
    )
    return tmp


async def _launch_persistent_copy(
    chrome_profile_path: str,
    chrome_profile_name: str,
    *,
    headless: bool,
) -> tuple[object, object, str, bool]:
    """Copied-profile mode (unused at runtime): launch Playwright against a temp profile copy."""
    from playwright.async_api import async_playwright

    tmp_dir = _copy_profile_to_temp(chrome_profile_path, chrome_profile_name)

    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=tmp_dir,
        headless=headless,
        channel="chrome",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            f"--profile-directory={chrome_profile_name}",
        ],
        ignore_default_args=[
            "--enable-automation",
            "--profile-directory=Guest Profile",
        ],
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        timezone_id="America/New_York",
        viewport={"width": 1280, "height": 900},
        java_script_enabled=True,
        bypass_csp=True,
        accept_downloads=False,
    )
    logger.info(
        "Browser context created from temp copy of %s (profile: %s, headless=%s)",
        chrome_profile_path,
        chrome_profile_name,
        headless,
    )
    return pw, context, tmp_dir, False


async def _connect_cdp(cdp_url: str) -> tuple[object, object, None, bool]:
    """Attach to an already running Chrome with remote debugging enabled."""
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(cdp_url)
    contexts = browser.contexts
    if not contexts:
        await pw.stop()
        raise RuntimeError(
            "Chrome reported no browser contexts over CDP — open at least one tab/window."
        )
    if len(contexts) > 1:
        logger.warning(
            "Multiple browser contexts over CDP (%d); using the first one.",
            len(contexts),
        )
    context = contexts[0]
    logger.info("Connected to Chrome via CDP at %s", cdp_url)
    return pw, context, None, True


async def create_browser_context(
    chrome_profile_path: str,
    chrome_profile_name: str = "Default",
    *,
    headless: bool = True,
):
    """Copied-profile mode (unused at runtime): backward-compatible launch helper."""
    pw, ctx, tmp, _is_cdp = await _launch_persistent_copy(
        chrome_profile_path, chrome_profile_name, headless=headless
    )
    return pw, ctx, tmp


async def create_browser_session_from_settings(settings: dict) -> tuple[
    object | None, object | None, str | None, bool
]:
    """Build a Playwright session from Settings (CDP URL only)."""
    cdp_url = (settings.get("chrome_cdp_url") or "").strip()
    if cdp_url:
        return await _connect_cdp(cdp_url)
    return None, None, None, False


async def close_browser_context(
    pw,
    context,
    tmp_dir=None,
    *,
    is_cdp: bool = False,
):
    """Close Playwright resources and remove temp profile copy when applicable."""
    if not pw:
        return
    try:
        if is_cdp:
            browser = getattr(context, "browser", None)
            if browser:
                await browser.close()
        else:
            await context.close()
    except Exception:
        logger.exception("Error closing browser context")
    try:
        await pw.stop()
    except Exception:
        logger.exception("Error stopping Playwright")
    if tmp_dir:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.info("Cleaned up temp browser profile %s", tmp_dir)
        except Exception:
            logger.exception("Error cleaning up temp dir %s", tmp_dir)


_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = { runtime: {} };
"""


async def browse_page(context, url: str, timeout: int = 30_000) -> str:
    """Open a page, render it, and return clean text content plus discovered links."""
    page = await context.new_page()
    try:
        await page.add_init_script(_STEALTH_JS)

        response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            await page.wait_for_load_state("networkidle", timeout=min(timeout, 15_000))
        except Exception:
            pass

        status = response.status if response else 0
        if status >= 400:
            return f"Error: HTTP {status} when loading {url}"

        html = await page.content()
        text, links = _extract_content(html, url)

        parts = [f"--- Content of {url} ---\n"]
        if text:
            truncated = text[:MAX_TEXT_LENGTH]
            if len(text) > MAX_TEXT_LENGTH:
                truncated += "\n\n[... content truncated ...]"
            parts.append(truncated)
        else:
            parts.append("(No text content extracted)")

        if links:
            parts.append(f"\n\n--- Links found on page ({len(links)} total) ---")
            for label, href in links[:MAX_LINKS]:
                parts.append(f"- [{label}]({href})")
            if len(links) > MAX_LINKS:
                parts.append(f"  ... and {len(links) - MAX_LINKS} more links")

        return "\n".join(parts)

    except Exception as e:
        return f"Error browsing {url}: {e}"
    finally:
        await page.close()


def _extract_content(html: str, base_url: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse HTML into clean text and a list of ``(label, absolute_url)`` links."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    links: list[tuple[str, str]] = []
    seen_hrefs: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen_hrefs:
            continue
        seen_hrefs.add(absolute)
        label = a.get_text(strip=True) or href
        label = label[:120]
        links.append((label, absolute))

    return clean_text, links
