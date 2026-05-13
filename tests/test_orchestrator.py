"""Phase 4 — Orchestrator tests.

Tier 1: unit tests (hardcoded fixtures, no API or browser calls).
Tier 2: e2e integration tests (live API + live Playwright, marked with @pytest.mark.e2e).
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from orchestrator import MAX_RETRIES, Orchestrator

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hardcoded_analyst_output() -> dict[str, Any]:
    return {
        "title": "TC-001 — Add a New Todo Item",
        "preconditions": ["The application is accessible at https://demo.playwright.dev/todomvc"],
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to https://demo.playwright.dev/todomvc",
                "expected_result": "TodoMVC app is displayed",
            }
        ],
        "assertions": ["The todo item is visible in the list"],
        "test_data": {
            "app_url": "https://demo.playwright.dev/todomvc",
            "todo_text": "Buy groceries",
        },
    }


@pytest.fixture
def hardcoded_browser_output() -> dict[str, Any]:
    return {
        "url": "https://demo.playwright.dev/todomvc",
        "page_title": "TodoMVC",
        "interactive_elements": [
            {
                "type": "input",
                "label": "New Todo Input",
                "selector": ".new-todo",
                "placeholder": "What needs to be done?",
            }
        ],
        "forms": [],
        "navigation": {"links": [], "current_path": "/"},
        "page_structure": "Single-page todo application.",
        "raw_observations": "TodoMVC app loaded.",
    }


@pytest.fixture
def hardcoded_coder_output() -> dict[str, Any]:
    return {
        "script": (
            "import { test, expect } from '@playwright/test';\n"
            "test('add todo', async ({ page }) => { await page.goto('https://demo.playwright.dev/todomvc'); });"
        )
    }


def _make_orchestrator_with_stubs(
    analyst_out: dict[str, Any],
    browser_out: dict[str, Any],
    coder_out: dict[str, Any],
    reviewer_side_effects: list[dict[str, Any]] | None = None,
) -> Orchestrator:
    """Build an Orchestrator whose agent calls return preset values (no network, no browser)."""
    llm = MagicMock()
    orch = Orchestrator(llm=llm)

    orch._analyst.run = MagicMock(return_value=analyst_out)  # type: ignore[method-assign]
    # Mock _run_browser (the sync wrapper) so no Playwright is launched in unit tests
    orch._run_browser = MagicMock(return_value=browser_out)  # type: ignore[method-assign]
    orch._coder.run = MagicMock(return_value=coder_out)  # type: ignore[method-assign]

    if reviewer_side_effects is not None:
        orch._reviewer.run = MagicMock(side_effect=reviewer_side_effects)  # type: ignore[method-assign]

    return orch


# ---------------------------------------------------------------------------
# Tier 1 — Unit tests
# ---------------------------------------------------------------------------


def test_orchestrator_routes_flow_a_when_repo_url_present(
    hardcoded_analyst_output: dict[str, Any],
    hardcoded_browser_output: dict[str, Any],
    hardcoded_coder_output: dict[str, Any],
) -> None:
    orch = _make_orchestrator_with_stubs(
        hardcoded_analyst_output, hardcoded_browser_output, hardcoded_coder_output
    )
    result = orch.run(
        {
            "test_case": "dummy",
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": "https://github.com/example/repo",
        }
    )
    assert result["flow"] == "A"


def test_orchestrator_routes_flow_b_when_repo_url_absent(
    hardcoded_analyst_output: dict[str, Any],
    hardcoded_browser_output: dict[str, Any],
    hardcoded_coder_output: dict[str, Any],
) -> None:
    orch = _make_orchestrator_with_stubs(
        hardcoded_analyst_output, hardcoded_browser_output, hardcoded_coder_output
    )
    result = orch.run(
        {
            "test_case": "dummy",
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": None,
        }
    )
    assert result["flow"] == "B"


def test_orchestrator_output_has_required_keys(
    hardcoded_analyst_output: dict[str, Any],
    hardcoded_browser_output: dict[str, Any],
    hardcoded_coder_output: dict[str, Any],
) -> None:
    orch = _make_orchestrator_with_stubs(
        hardcoded_analyst_output, hardcoded_browser_output, hardcoded_coder_output
    )
    result = orch.run(
        {
            "test_case": "dummy",
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": None,
        }
    )
    required_keys = {
        "flow",
        "analyst_output",
        "browser_output",
        "coder_output",
        "reviewer_verdict",
        "retries",
        "script",
    }
    assert required_keys.issubset(result.keys())


def test_orchestrator_retry_hook_increments_on_fail(
    hardcoded_analyst_output: dict[str, Any],
    hardcoded_browser_output: dict[str, Any],
    hardcoded_coder_output: dict[str, Any],
) -> None:
    """Reviewer returns FAIL twice then PASS — retries should be 2."""
    reviewer_responses = [
        {"verdict": "FAIL", "issues": ["bad selector"], "suggestions": []},
        {"verdict": "FAIL", "issues": ["still bad"], "suggestions": []},
        {"verdict": "PASS", "issues": [], "suggestions": []},
    ]
    orch = _make_orchestrator_with_stubs(
        hardcoded_analyst_output,
        hardcoded_browser_output,
        hardcoded_coder_output,
        reviewer_side_effects=reviewer_responses,
    )
    result = orch.run(
        {
            "test_case": "dummy",
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": None,
        }
    )
    assert result["retries"] == 2


def test_orchestrator_retry_hook_respects_max_retries(
    hardcoded_analyst_output: dict[str, Any],
    hardcoded_browser_output: dict[str, Any],
    hardcoded_coder_output: dict[str, Any],
) -> None:
    """Reviewer always returns FAIL — pipeline must stop at MAX_RETRIES and still return."""
    reviewer_responses = [{"verdict": "FAIL", "issues": ["always bad"], "suggestions": []}] * (
        MAX_RETRIES + 5
    )
    orch = _make_orchestrator_with_stubs(
        hardcoded_analyst_output,
        hardcoded_browser_output,
        hardcoded_coder_output,
        reviewer_side_effects=reviewer_responses,
    )
    result = orch.run(
        {
            "test_case": "dummy",
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": None,
        }
    )
    assert result["retries"] == MAX_RETRIES - 1
    assert "script" in result


def test_reviewer_stub_returns_pass_verdict() -> None:
    from agents.reviewer_agent import ReviewerAgent

    llm = MagicMock()
    reviewer = ReviewerAgent(llm)
    result = reviewer.run({"script": "some script"})
    assert result["verdict"] == "PASS"
    assert result["issues"] == []
    assert result["suggestions"] == []


def test_repo_reader_stub_returns_dict() -> None:
    from agents.repo_reader_agent import RepoReaderAgent

    llm = MagicMock()
    agent = RepoReaderAgent(llm)
    result = agent.run({"repo_url": "https://github.com/example/repo"})
    assert isinstance(result, dict)


def test_scaffold_stub_returns_dict() -> None:
    from agents.scaffold_agent import ScaffoldAgent

    llm = MagicMock()
    agent = ScaffoldAgent(llm)
    result = agent.run({})
    assert isinstance(result, dict)


def test_git_stub_returns_dict() -> None:
    from agents.git_agent import GitAgent

    llm = MagicMock()
    agent = GitAgent(llm)
    result = agent.run({"script": "some script"})
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tier 2 — E2E integration tests
# ---------------------------------------------------------------------------

ADD_TODO_TEST_CASE = """
TEST CASE: TC-001 — Add a New Todo Item

Objective:
Verify that a user can add a new todo item to the TodoMVC list and that it appears correctly.

Preconditions:
- The application is accessible at https://demo.playwright.dev/todomvc

Test Steps:
Step 1:
  Action: Navigate to https://demo.playwright.dev/todomvc
  Expected Result: The TodoMVC app is displayed with an input field placeholder "What needs to be done?"

Step 2:
  Action: Click on the input field and type "Buy groceries"
  Expected Result: The text "Buy groceries" appears in the input field

Step 3:
  Action: Press the Enter key
  Expected Result: A new todo item "Buy groceries" appears in the list

Assertions:
- The todo item "Buy groceries" is visible in the list after submission
- The input field is cleared after the todo is added

Test Data:
  app_url: https://demo.playwright.dev/todomvc
  todo_text: Buy groceries
"""


@pytest.mark.e2e
def test_orchestrator_full_flow_b_todomvc() -> None:
    """Flow B (no repo_url) — full live pipeline with TodoMVC TC-001."""
    from llm.anthropic_provider import AnthropicProvider

    llm = AnthropicProvider()
    orch = Orchestrator(llm=llm)
    result = orch.run(
        {
            "test_case": ADD_TODO_TEST_CASE,
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": None,
        }
    )
    assert result["flow"] == "B"
    assert isinstance(result["script"], str)
    assert len(result["script"]) > 0


@pytest.mark.e2e
def test_orchestrator_full_flow_a_todomvc() -> None:
    """Flow A (with repo_url) — full live pipeline with TodoMVC TC-001."""
    from llm.anthropic_provider import AnthropicProvider

    llm = AnthropicProvider()
    orch = Orchestrator(llm=llm)
    result = orch.run(
        {
            "test_case": ADD_TODO_TEST_CASE,
            "staging_url": "https://demo.playwright.dev/todomvc",
            "repo_url": "https://github.com/example/stub",
        }
    )
    assert result["flow"] == "A"
    assert isinstance(result["script"], str)
    assert len(result["script"]) > 0
