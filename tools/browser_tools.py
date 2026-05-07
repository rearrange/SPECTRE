"""Async Playwright wrappers for SPECTRE browser interactions."""

import os
from pathlib import Path
from typing import Any

from playwright.async_api import Page


async def browse_url(page: Page, url: str) -> str:
    """Navigate to url, wait for networkidle, return page HTML content."""
    await page.goto(url, wait_until="networkidle")
    return await page.content()


async def get_page_title(page: Page) -> str:
    """Return the page title."""
    return await page.title()


async def get_interactive_elements(page: Page) -> list[dict[str, Any]]:
    """Return list of interactive elements found on the page.

    Each element dict has: type, label, selector, placeholder.
    Label priority: aria-label > placeholder > text content > id > tag.
    Selector priority: data-testid > aria-label > id > tag.
    """
    css_selector = "input, button, select, textarea, a[href]"
    handles = await page.query_selector_all(css_selector)
    elements: list[dict[str, Any]] = []

    for handle in handles:
        tag = str(await handle.evaluate("el => el.tagName")).lower()
        aria_label = (await handle.get_attribute("aria-label") or "").strip()
        placeholder = await handle.get_attribute("placeholder")
        id_attr = (await handle.get_attribute("id") or "").strip()
        data_testid = await handle.get_attribute("data-testid")

        try:
            text = (await handle.inner_text()).strip()[:100]
        except Exception:
            text = ""

        label = aria_label or (placeholder or "") or text or id_attr or tag

        if data_testid:
            elem_selector = f"[data-testid='{data_testid}']"
        elif aria_label:
            elem_selector = f"[aria-label='{aria_label}']"
        elif id_attr:
            elem_selector = f"#{id_attr}"
        else:
            elem_selector = tag

        elements.append(
            {
                "type": tag,
                "label": label,
                "selector": elem_selector,
                "placeholder": placeholder,
            }
        )

    return elements


async def take_screenshot(page: Page, name: str) -> str | None:
    """Save screenshot to output/screenshots/{name}.png only if DEBUG_SCREENSHOTS=true.

    Returns the file path if saved, None if skipped.
    """
    if os.environ.get("DEBUG_SCREENSHOTS", "").lower() != "true":
        return None
    path = Path("output") / "screenshots" / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path))
    return str(path)
