from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from playwright.async_api import Browser, Page, async_playwright

from agents.analyst_agent import AnalystAgent
from agents.browser_agent import BrowserAgent
from llm.anthropic_provider import AnthropicProvider


@pytest.fixture
def sample_test_case_add_todo() -> str:
    return """
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


@pytest.fixture
def sample_test_case_complete_todo() -> str:
    return """
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


@pytest.fixture
def analyst_output_add_todo() -> dict:
    """Hardcoded AnalystAgent output for TC-001. No API call."""
    return {
        "title": "TC-001 — Add a New Todo Item",
        "preconditions": [
            "The application is accessible at https://demo.playwright.dev/todomvc",
            "The todo list is empty or has existing items",
        ],
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to https://demo.playwright.dev/todomvc",
                "expected_result": "The TodoMVC app is displayed with an input field placeholder 'What needs to be done?'",
            },
            {
                "step_number": 2,
                "action": "Click on the input field at the top of the page",
                "expected_result": "The input field receives focus",
            },
            {
                "step_number": 3,
                "action": "Type 'Buy groceries' into the input field",
                "expected_result": "The text 'Buy groceries' appears in the input field",
            },
            {
                "step_number": 4,
                "action": "Press the Enter key",
                "expected_result": "A new todo item 'Buy groceries' appears in the list",
            },
            {
                "step_number": 5,
                "action": "Verify the todo item is visible in the list",
                "expected_result": "The item 'Buy groceries' is displayed and the input field is cleared",
            },
        ],
        "assertions": [
            "The todo item 'Buy groceries' is visible in the list after submission",
            "The input field is cleared after the todo is added",
            "The todo count shows 1 item left",
        ],
        "test_data": {
            "app_url": "https://demo.playwright.dev/todomvc",
            "todo_text": "Buy groceries",
        },
    }


@pytest.fixture
def analyst_output_complete_todo() -> dict:
    """Hardcoded AnalystAgent output for TC-002. No API call."""
    return {
        "title": "TC-002 — Complete a Todo Item",
        "preconditions": [
            "The application is accessible at https://demo.playwright.dev/todomvc",
            "At least one todo item exists in the list: 'Buy groceries'",
        ],
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to https://demo.playwright.dev/todomvc",
                "expected_result": "The TodoMVC app is displayed with the existing todo item visible",
            },
            {
                "step_number": 2,
                "action": "Add a todo item 'Buy groceries' by typing it in the input and pressing Enter",
                "expected_result": "'Buy groceries' appears in the todo list",
            },
            {
                "step_number": 3,
                "action": "Click the circular checkbox to the left of 'Buy groceries'",
                "expected_result": "The checkbox becomes checked and the item text is struck through",
            },
            {
                "step_number": 4,
                "action": "Click the 'Completed' filter link at the bottom of the page",
                "expected_result": "Only 'Buy groceries' is displayed under the Completed filter",
            },
            {
                "step_number": 5,
                "action": "Click the 'Active' filter link",
                "expected_result": "No items are displayed under the Active filter",
            },
        ],
        "assertions": [
            "The completed item has a strikethrough style applied",
            "The item appears under the Completed filter",
            "The item does not appear under the Active filter",
            "The item count shows '0 items left' after completion",
        ],
        "test_data": {
            "app_url": "https://demo.playwright.dev/todomvc",
            "todo_text": "Buy groceries",
        },
    }


@pytest.fixture
def browser_output_todomvc() -> dict:
    """
    Hardcoded BrowserAgent output for demo.playwright.dev/todomvc.
    Represents what BrowserAgent actually returns after Phase 2.
    No API call, no browser launch.
    """
    return {
        "url": "https://demo.playwright.dev/todomvc",
        "page_title": "TodoMVC",
        "interactive_elements": [
            {
                "type": "input",
                "label": "New Todo Input",
                "selector": ".new-todo",
                "placeholder": "What needs to be done?",
            },
            {
                "type": "checkbox",
                "label": "Toggle All",
                "selector": ".toggle-all",
                "placeholder": None,
            },
            {
                "type": "checkbox",
                "label": "Todo Item Toggle",
                "selector": ".todo-list li .toggle",
                "placeholder": None,
            },
            {
                "type": "button",
                "label": "Clear Completed",
                "selector": ".clear-completed",
                "placeholder": None,
            },
        ],
        "forms": [],
        "navigation": {
            "links": [
                {"text": "All", "href": "#/"},
                {"text": "Active", "href": "#/active"},
                {"text": "Completed", "href": "#/completed"},
            ],
            "current_path": "/",
        },
        "page_structure": "Single-page todo application. Contains a header with a text input for adding todos, a main section with a list of todo items each having a checkbox and label, and a footer with item count, filter links (All, Active, Completed), and a Clear Completed button.",
        "raw_observations": "TodoMVC app loaded. Input field present with placeholder 'What needs to be done?'. Todo list is empty on initial load. Footer is hidden when list is empty. Filter links visible when items exist.",
    }


@pytest.fixture
def analyst_agent() -> AnalystAgent:
    llm = AnthropicProvider()
    return AnalystAgent(llm)


@pytest.fixture
def browser_agent() -> BrowserAgent:
    llm = AnthropicProvider()
    return BrowserAgent(llm)


@pytest_asyncio.fixture
async def browser() -> AsyncGenerator[Browser]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser: Browser) -> AsyncGenerator[Page]:
    page = await browser.new_page()
    yield page
    await page.close()
