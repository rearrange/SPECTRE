"""Contract tests for BrowserAgent — written before implementation (TDD)."""

from typing import Any

from playwright.async_api import Page

from agents.browser_agent import BrowserAgent

URL = "https://demo.playwright.dev/todomvc"


async def test_browser_agent_returns_url(browser_agent: BrowserAgent, page: Page) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    assert result["url"] == URL


async def test_browser_agent_returns_page_title(browser_agent: BrowserAgent, page: Page) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    assert isinstance(result["page_title"], str)
    assert len(result["page_title"]) > 0


async def test_browser_agent_returns_interactive_elements(
    browser_agent: BrowserAgent, page: Page
) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    assert isinstance(result["interactive_elements"], list)
    assert len(result["interactive_elements"]) >= 1


async def test_browser_agent_interactive_elements_have_required_fields(
    browser_agent: BrowserAgent, page: Page
) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    for element in result["interactive_elements"]:
        assert "type" in element
        assert "label" in element
        assert "selector" in element
        assert isinstance(element["type"], str) and element["type"]
        assert isinstance(element["label"], str) and element["label"]
        assert isinstance(element["selector"], str) and element["selector"]


async def test_browser_agent_returns_navigation(browser_agent: BrowserAgent, page: Page) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    assert isinstance(result["navigation"], dict)
    assert "links" in result["navigation"]
    assert "current_path" in result["navigation"]
    assert isinstance(result["navigation"]["links"], list)
    assert isinstance(result["navigation"]["current_path"], str)


async def test_browser_agent_returns_page_structure(
    browser_agent: BrowserAgent, page: Page
) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    assert isinstance(result["page_structure"], str)
    assert len(result["page_structure"]) > 0


async def test_browser_agent_returns_valid_json_structure(
    browser_agent: BrowserAgent, page: Page
) -> None:
    result: dict[str, Any] = await browser_agent.run({"url": URL, "page": page})
    required_keys = {
        "url",
        "page_title",
        "interactive_elements",
        "forms",
        "navigation",
        "page_structure",
        "raw_observations",
    }
    assert required_keys.issubset(result.keys())
    assert isinstance(result["url"], str)
    assert isinstance(result["page_title"], str)
    assert isinstance(result["interactive_elements"], list)
    assert isinstance(result["forms"], list)
    assert isinstance(result["navigation"], dict)
    assert isinstance(result["page_structure"], str)
    assert isinstance(result["raw_observations"], str)
