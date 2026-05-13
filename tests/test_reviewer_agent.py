"""Phase 5 — ReviewerAgent tests.

Tier 1: unit tests (mocked LLM, no API).
Tier 2: e2e integration tests (live API, marked with @pytest.mark.e2e).
"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from agents.reviewer_agent import ReviewerAgent, ReviewerError
from llm.base import LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GOOD_SCRIPT = """\
import { test, expect } from '@playwright/test';

test.describe('TC-001 — Add a New Todo Item', () => {
  test('adds a todo item to the list', async ({ page }) => {
    // Arrange
    await page.goto('https://demo.playwright.dev/todomvc');

    // Act
    const todoInput = page.getByPlaceholder('What needs to be done?');
    await todoInput.fill('Buy groceries');
    await todoInput.press('Enter');

    // Assert
    await expect(
      page.getByRole('list').getByRole('listitem').filter({ hasText: 'Buy groceries' })
    ).toBeVisible();
  });
});
"""

BROKEN_SCRIPT = """\
import { test } from '@playwright/test';

test('Login test', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.waitForTimeout(3000);
  await page.locator('.username-field').fill('admin');
  await page.locator('.password-field').fill('password');
  await page.locator('.submit-btn').click();
  // No assertions at all
});
"""

PASS_RESPONSE = json.dumps(
    {
        "verdict": "PASS",
        "issues": [],
        "suggestions": ["Consider using getByRole for the submit button"],
    }
)

FAIL_RESPONSE = json.dumps(
    {
        "verdict": "FAIL",
        "issues": [
            "Step 3 (verify error message) has no corresponding expect() assertion",
            "Raw CSS selector '.btn-submit' used — prefer getByRole or getByTestId",
        ],
        "suggestions": [
            "Add: await expect(page.getByText('Invalid credentials')).toBeVisible()",
            "Replace: page.locator('.btn-submit') with page.getByRole('button', { name: 'Submit' })",
        ],
    }
)


def _make_reviewer(llm_response_content: str) -> ReviewerAgent:
    llm = MagicMock()
    llm.complete.return_value = LLMResponse(
        content=llm_response_content,
        model="mock",
        input_tokens=10,
        output_tokens=10,
    )
    return ReviewerAgent(llm)


@pytest.fixture
def analyst_output_add_todo() -> dict[str, Any]:
    return {
        "title": "TC-001 — Add a New Todo Item",
        "preconditions": ["The application is accessible at https://demo.playwright.dev/todomvc"],
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to https://demo.playwright.dev/todomvc",
                "expected_result": "TodoMVC app is displayed",
            },
            {
                "step_number": 2,
                "action": "Type 'Buy groceries' into the input field",
                "expected_result": "Text appears in input",
            },
            {
                "step_number": 3,
                "action": "Press the Enter key",
                "expected_result": "Todo item appears in the list",
            },
        ],
        "assertions": ["The todo item 'Buy groceries' is visible in the list after submission"],
        "test_data": {
            "app_url": "https://demo.playwright.dev/todomvc",
            "todo_text": "Buy groceries",
        },
    }


# ---------------------------------------------------------------------------
# Tier 1 — Unit tests
# ---------------------------------------------------------------------------


def test_reviewer_returns_pass_for_valid_script(analyst_output_add_todo: dict[str, Any]) -> None:
    reviewer = _make_reviewer(PASS_RESPONSE)
    result = reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output_add_todo})
    assert result["verdict"] == "PASS"


def test_reviewer_returns_fail_for_bad_script(analyst_output_add_todo: dict[str, Any]) -> None:
    reviewer = _make_reviewer(FAIL_RESPONSE)
    result = reviewer.run({"script": BROKEN_SCRIPT, "analyst_output": analyst_output_add_todo})
    assert result["verdict"] == "FAIL"
    assert len(result["issues"]) > 0


def test_reviewer_raises_on_empty_llm_response(analyst_output_add_todo: dict[str, Any]) -> None:
    reviewer = _make_reviewer("")
    with pytest.raises(ReviewerError):
        reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output_add_todo})


def test_reviewer_raises_on_unparseable_llm_response(
    analyst_output_add_todo: dict[str, Any],
) -> None:
    reviewer = _make_reviewer("not json")
    with pytest.raises(ReviewerError):
        reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output_add_todo})


def test_reviewer_pass_has_empty_issues(analyst_output_add_todo: dict[str, Any]) -> None:
    reviewer = _make_reviewer(PASS_RESPONSE)
    result = reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output_add_todo})
    assert result["issues"] == []


def test_reviewer_suggestions_present_on_pass(analyst_output_add_todo: dict[str, Any]) -> None:
    reviewer = _make_reviewer(PASS_RESPONSE)
    result = reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output_add_todo})
    assert isinstance(result["suggestions"], list)
    assert len(result["suggestions"]) > 0


def test_reviewer_fail_has_non_empty_issues(analyst_output_add_todo: dict[str, Any]) -> None:
    reviewer = _make_reviewer(FAIL_RESPONSE)
    result = reviewer.run({"script": BROKEN_SCRIPT, "analyst_output": analyst_output_add_todo})
    assert result["verdict"] == "FAIL"
    assert len(result["issues"]) >= 1


def test_reviewer_sends_both_script_and_analyst_output_to_llm(
    analyst_output_add_todo: dict[str, Any],
) -> None:
    llm = MagicMock()
    llm.complete.return_value = LLMResponse(
        content=PASS_RESPONSE,
        model="mock",
        input_tokens=10,
        output_tokens=10,
    )
    reviewer = ReviewerAgent(llm)
    reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output_add_todo})

    assert llm.complete.called
    call_kwargs = llm.complete.call_args
    user_prompt = call_kwargs[1].get("user") or call_kwargs[0][1]
    assert "Buy groceries" in user_prompt  # analyst_output content
    assert "page.goto" in user_prompt  # script content


# ---------------------------------------------------------------------------
# Tier 2 — E2E integration tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_reviewer_e2e_pass_on_real_script() -> None:
    """Feed a known-good Playwright TS script + matching analyst output → reviewer returns PASS."""
    from llm.anthropic_provider import AnthropicProvider

    llm = AnthropicProvider()
    reviewer = ReviewerAgent(llm)

    analyst_output: dict[str, Any] = {
        "title": "TC-001 — Add a New Todo Item",
        "preconditions": ["The application is accessible at https://demo.playwright.dev/todomvc"],
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to https://demo.playwright.dev/todomvc",
                "expected_result": "TodoMVC app is displayed",
            },
            {
                "step_number": 2,
                "action": "Type 'Buy groceries' into the input field and press Enter",
                "expected_result": "Todo item 'Buy groceries' appears in the list",
            },
        ],
        "assertions": ["The todo item 'Buy groceries' is visible in the list after submission"],
        "test_data": {
            "app_url": "https://demo.playwright.dev/todomvc",
            "todo_text": "Buy groceries",
        },
    }

    result = reviewer.run({"script": GOOD_SCRIPT, "analyst_output": analyst_output})
    assert result["verdict"] == "PASS"
    assert isinstance(result["issues"], list)
    assert isinstance(result["suggestions"], list)


@pytest.mark.e2e
def test_reviewer_e2e_fail_on_bad_script() -> None:
    """Feed a deliberately broken script → reviewer returns FAIL with non-empty issues."""
    from llm.anthropic_provider import AnthropicProvider

    llm = AnthropicProvider()
    reviewer = ReviewerAgent(llm)

    analyst_output: dict[str, Any] = {
        "title": "Login Test",
        "preconditions": ["The application is accessible at https://example.com/login"],
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to https://example.com/login",
                "expected_result": "Login page is displayed",
            },
            {
                "step_number": 2,
                "action": "Enter username 'admin' and password 'password'",
                "expected_result": "Credentials are entered",
            },
            {
                "step_number": 3,
                "action": "Click the submit button",
                "expected_result": "User is logged in and redirected to dashboard",
            },
        ],
        "assertions": [
            "User is redirected to the dashboard",
            "Welcome message is displayed",
        ],
        "test_data": {
            "app_url": "https://example.com/login",
            "username": "admin",
            "password": "password",
        },
    }

    result = reviewer.run({"script": BROKEN_SCRIPT, "analyst_output": analyst_output})
    assert result["verdict"] == "FAIL"
    assert len(result["issues"]) > 0
