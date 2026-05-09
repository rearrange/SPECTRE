"""
Tests for CoderAgent — written BEFORE implementation (TDD).

These tests define the contract the CoderAgent must satisfy.
All Tier 1 tests use hardcoded fixtures (no API, no browser).
Tier 2 e2e tests use the live Analyst → Browser → Coder chain.
"""

from typing import Any

import pytest

from agents.coder_agent import CoderAgent
from llm.anthropic_provider import AnthropicProvider


@pytest.fixture
def coder_agent() -> CoderAgent:
    llm = AnthropicProvider()
    return CoderAgent(llm)


# ---------------------------------------------------------------------------
# Tier 1 — Fast unit tests (hardcoded fixtures, no API, no browser)
# ---------------------------------------------------------------------------


def test_coder_returns_script_key(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Result must contain a 'script' key with a non-empty string value."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "script" in result
    assert isinstance(result["script"], str)
    assert len(result["script"]) > 0


def test_coder_script_has_playwright_import(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must contain the standard Playwright TypeScript import."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "from '@playwright/test'" in result["script"]


def test_coder_script_has_test_block(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must contain at least one test() block."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "test(" in result["script"]


def test_coder_script_has_describe_block(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must wrap tests in a test.describe() block."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "test.describe(" in result["script"]


def test_coder_script_has_expect(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must contain at least one expect() assertion."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "expect(" in result["script"]


def test_coder_script_references_app_url(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must reference the app URL from test data."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "demo.playwright.dev/todomvc" in result["script"]


def test_coder_script_has_goto(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must contain at least one page.goto() navigation call."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert ".goto(" in result["script"]


def test_coder_script_no_positional_selectors(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must not use nth-child or nth-of-type positional selectors."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    assert "nth-child" not in result["script"]
    assert "nth-of-type" not in result["script"]


def test_coder_script_has_aaa_comments(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must contain AAA structure comments."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    script = result["script"]
    assert any(marker in script for marker in ("// Arrange", "// Act", "// Assert"))


def test_coder_script_covers_all_steps(
    coder_agent: CoderAgent,
    analyst_output_add_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """Script must have at least as many await calls as analyst steps."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_add_todo, "browser_output": browser_output_todomvc}
    )
    step_count = len(analyst_output_add_todo["steps"])
    await_count = result["script"].count("await ")
    assert await_count >= step_count


def test_coder_handles_complete_todo_input(
    coder_agent: CoderAgent,
    analyst_output_complete_todo: dict,
    browser_output_todomvc: dict,
) -> None:
    """CoderAgent must handle TC-002 input without error and return a valid script."""
    result = coder_agent.run(
        {"analyst_output": analyst_output_complete_todo, "browser_output": browser_output_todomvc}
    )
    assert "script" in result
    assert isinstance(result["script"], str)
    assert len(result["script"]) > 0
    assert "test(" in result["script"]


# ---------------------------------------------------------------------------
# Tier 2 — E2E integration tests (live API + live browser, session-scoped)
# ---------------------------------------------------------------------------

_TC001_TEXT = """
TEST CASE: TC-001 — Add a New Todo Item

Objective:
Verify that a user can add a new todo item to the TodoMVC list and that it appears correctly.

Preconditions:
- The application is accessible at https://demo.playwright.dev/todomvc
- The todo list is empty or has existing items

Test Steps:
Step 1:
  Action: Navigate to https://demo.playwright.dev/todomvc
  Expected Result: The TodoMVC app is displayed with an input field placeholder "What needs to be done?"

Step 2:
  Action: Click on the input field at the top of the page
  Expected Result: The input field receives focus

Step 3:
  Action: Type "Buy groceries" into the input field
  Expected Result: The text "Buy groceries" appears in the input field

Step 4:
  Action: Press the Enter key
  Expected Result: A new todo item "Buy groceries" appears in the list below the input field

Step 5:
  Action: Verify the todo item is visible in the list
  Expected Result: The item "Buy groceries" is displayed and the input field is cleared

Assertions:
- The todo item "Buy groceries" is visible in the list after submission
- The input field is cleared after the todo is added
- The todo count shows 1 item left

Test Data:
  app_url: https://demo.playwright.dev/todomvc
  todo_text: Buy groceries
"""

_TC002_TEXT = """
TEST CASE: TC-002 — Complete a Todo Item

Objective:
Verify that a user can mark a todo item as complete and that it is visually distinguished from
active items.

Preconditions:
- The application is accessible at https://demo.playwright.dev/todomvc
- At least one todo item exists in the list: "Buy groceries"

Test Steps:
Step 1:
  Action: Navigate to https://demo.playwright.dev/todomvc
  Expected Result: The TodoMVC app is displayed with the existing todo item "Buy groceries" visible

Step 2:
  Action: Add a todo item "Buy groceries" by typing it in the input and pressing Enter
  Expected Result: "Buy groceries" appears in the todo list

Step 3:
  Action: Click the circular checkbox to the left of "Buy groceries"
  Expected Result: The checkbox becomes checked and the item text is visually struck through

Step 4:
  Action: Click the "Completed" filter link at the bottom of the page
  Expected Result: Only "Buy groceries" is displayed under the Completed filter

Step 5:
  Action: Click the "Active" filter link
  Expected Result: No items are displayed under the Active filter

Assertions:
- The completed item has a strikethrough style applied
- The item appears under the Completed filter
- The item does not appear under the Active filter
- The item count shows "0 items left" after completion

Test Data:
  app_url: https://demo.playwright.dev/todomvc
  todo_text: Buy groceries
"""


@pytest.fixture(scope="session")
def e2e_coder_output_add_todo() -> dict[str, Any]:
    """Runs the full Analyst → Browser → Coder chain for TC-001 once per session."""
    import asyncio

    from playwright.async_api import async_playwright

    from agents.analyst_agent import AnalystAgent
    from agents.browser_agent import BrowserAgent
    from agents.coder_agent import CoderAgent
    from llm.anthropic_provider import AnthropicProvider

    llm = AnthropicProvider()

    analyst = AnalystAgent(llm)
    analyst_output = analyst.run({"test_case": _TC001_TEXT})

    async def run_browser() -> dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                browser_agent = BrowserAgent(llm)
                return await browser_agent.run(
                    {"url": analyst_output["test_data"]["app_url"], "page": page}
                )
            finally:
                await page.close()
                await browser.close()

    browser_output = asyncio.run(run_browser())

    coder = CoderAgent(llm)
    return coder.run({"analyst_output": analyst_output, "browser_output": browser_output})


@pytest.fixture(scope="session")
def e2e_coder_output_complete_todo() -> dict[str, Any]:
    """Runs the full Analyst → Browser → Coder chain for TC-002 once per session."""
    import asyncio

    from playwright.async_api import async_playwright

    from agents.analyst_agent import AnalystAgent
    from agents.browser_agent import BrowserAgent
    from agents.coder_agent import CoderAgent
    from llm.anthropic_provider import AnthropicProvider

    llm = AnthropicProvider()

    analyst = AnalystAgent(llm)
    analyst_output = analyst.run({"test_case": _TC002_TEXT})

    async def run_browser() -> dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                browser_agent = BrowserAgent(llm)
                return await browser_agent.run(
                    {"url": analyst_output["test_data"]["app_url"], "page": page}
                )
            finally:
                await page.close()
                await browser.close()

    browser_output = asyncio.run(run_browser())

    coder = CoderAgent(llm)
    return coder.run({"analyst_output": analyst_output, "browser_output": browser_output})


@pytest.mark.e2e
def test_e2e_coder_add_todo_produces_script(e2e_coder_output_add_todo: dict[str, Any]) -> None:
    """Full chain for TC-001 must produce a valid Playwright TypeScript script."""
    assert isinstance(e2e_coder_output_add_todo["script"], str)
    assert len(e2e_coder_output_add_todo["script"]) > 0
    assert "test(" in e2e_coder_output_add_todo["script"]


@pytest.mark.e2e
def test_e2e_coder_complete_todo_produces_script(
    e2e_coder_output_complete_todo: dict[str, Any],
) -> None:
    """Full chain for TC-002 must produce a valid Playwright TypeScript script."""
    assert isinstance(e2e_coder_output_complete_todo["script"], str)
    assert len(e2e_coder_output_complete_todo["script"]) > 0
    assert "test(" in e2e_coder_output_complete_todo["script"]
