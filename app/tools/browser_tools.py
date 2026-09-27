"""Browser automation tools using Playwright.

These tools give the agent the ability to browse the web, interact with pages,
fill forms, click buttons, and extract information.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import structlog

from app.core.web_content_cleaner import clean_web_content
from app.tools import tool
from app.tools.browser_pool import get_browser_pool
from app.utils.ssrf import blocked_reason

logger = structlog.get_logger()

# Default screenshot target, resolved from the platform temp directory instead
# of a hardcoded path. Callers that need confidentiality should pass their own
# private path: the temp directory stays world-writable.
_DEFAULT_SCREENSHOT_PATH: str = str(Path(tempfile.gettempdir()) / "browser_screenshot.png")


async def _get_session(session_id: str) -> Any:
    """Get or create a pooled browser session."""
    return await get_browser_pool().acquire(session_id)


async def _get_or_create_page(session_id: str):
    """Get current page or create a new one."""
    session = await _get_session(session_id)
    context = session.context
    await _install_ssrf_route(context)
    pages = context.pages
    if pages:
        return pages[-1]
    return await context.new_page()


async def _install_ssrf_route(context: Any) -> None:
    """Validate every browser request before Playwright dispatches it."""
    if getattr(context, "_ssrf_route_installed", False):
        return

    async def _handle_route(route: Any) -> None:
        url = route.request.url
        reason = blocked_reason(url)
        if reason is not None:
            context._ssrf_blocked_reason = reason
            await route.abort()
            return
        await route.continue_()

    context._ssrf_blocked_reason = None
    await context.route("**/*", _handle_route)
    context._ssrf_route_installed = True


def _ssrf_error(context: Any) -> str | None:
    reason = getattr(context, "_ssrf_blocked_reason", None)
    if reason is None:
        return None
    return f"Error: request blocked by SSRF protection ({reason})"


async def close_session(session_id: str) -> None:
    """Close a single browser session."""
    await get_browser_pool().release(session_id)


async def close_all_sessions() -> None:
    """Close all browser sessions (app shutdown)."""
    await get_browser_pool().close_all()


def browser_pool_stats() -> dict[str, Any]:
    """Expose pool state for the health endpoint."""
    return get_browser_pool().stats()



@tool(description="Navigate to a URL and return the page title and content summary.")
async def browser_navigate(url: str, session_id: str = "default") -> str:
    """Navigate to URL in browser."""
    try:
        reason = blocked_reason(url)
        if reason is not None:
            return f"Error: request blocked by SSRF protection ({reason})"
        page = await _get_or_create_page(session_id)
        page.context._ssrf_blocked_reason = None
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if error := _ssrf_error(page.context):
            return error
        title = await page.title()
        raw_text = await page.inner_text("body")
        cleaned = clean_web_content("", raw_text)
        return f"Title: {title}\n\nContent (first 3000 chars):\n{cleaned[:3000]}"
    except Exception as e:
        if "page" in locals() and (error := _ssrf_error(page.context)):
            return error
        return f"Error navigating: {e!s}"


@tool(description="Take screenshot of a webpage. Returns file path.")
async def browser_screenshot(
    url: str,
    output_path: str = _DEFAULT_SCREENSHOT_PATH,
    session_id: str = "default",
) -> str:
    """Screenshot a webpage."""
    try:
        reason = blocked_reason(url)
        if reason is not None:
            return f"Error: request blocked by SSRF protection ({reason})"
        page = await _get_or_create_page(session_id)
        page.context._ssrf_blocked_reason = None
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if error := _ssrf_error(page.context):
            return error
        await page.screenshot(path=output_path, full_page=False)
        return output_path
    except Exception as e:
        if "page" in locals() and (error := _ssrf_error(page.context)):
            return error
        return f"Error: {e!s}"


@tool(description="Click an element on the current page by selector.")
async def browser_click(selector: str, session_id: str = "default") -> str:
    """Click element by CSS selector."""
    try:
        page = await _get_or_create_page(session_id)
        await page.click(selector, timeout=10000)
        return f"Clicked: {selector}"
    except Exception as e:
        return f"Error clicking: {e!s}"


@tool(description="Type text into an input field.")
async def browser_type(selector: str, text: str, session_id: str = "default") -> str:
    """Type text into input."""
    try:
        page = await _get_or_create_page(session_id)
        await page.fill(selector, text, timeout=10000)
        return f"Typed into {selector}"
    except Exception as e:
        return f"Error typing: {e!s}"


@tool(description="Extract all links from the current page.")
async def browser_extract_links(session_id: str = "default") -> str:
    """Extract all links from current page."""
    try:
        page = await _get_or_create_page(session_id)
        links = await page.eval_on_selector_all(
            "a[href]",
            "elements => elements.map(e => ({text: e.textContent.trim(), href: e.href}))",
        )
        formatted = [
            f"- {link['text'][:80]}\n  {link['href']}"
            for link in links[:30]
            if link["text"]
        ]
        return "\n".join(formatted) if formatted else "No links found"
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Extract text content from the current page.")
async def browser_extract_text(selector: str = "body", session_id: str = "default") -> str:
    """Extract text from page with noise filtering."""
    try:
        page = await _get_or_create_page(session_id)
        text = await page.inner_text(selector)
        cleaned = clean_web_content("", text)
        return cleaned[:10000]
    except Exception as e:
        return f"Error: {e!s}"
