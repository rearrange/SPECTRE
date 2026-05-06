"""
Tests for AnalystAgent — written BEFORE implementation (TDD).

These tests define the contract the AnalystAgent must satisfy.
All tests should FAIL initially and PASS after implementation.
"""

from agents.analyst_agent import AnalystAgent


def test_analyst_extracts_title(analyst_agent: AnalystAgent, sample_test_case_login: str) -> None:
    """The output must contain a non-empty title string."""
    result = analyst_agent.run({"test_case": sample_test_case_login})
    assert "title" in result
    assert isinstance(result["title"], str)
    assert len(result["title"]) > 0


def test_analyst_extracts_steps(analyst_agent: AnalystAgent, sample_test_case_login: str) -> None:
    """The output steps must be a list with at least one item."""
    result = analyst_agent.run({"test_case": sample_test_case_login})
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) >= 1


def test_analyst_steps_have_required_fields(
    analyst_agent: AnalystAgent, sample_test_case_login: str
) -> None:
    """Each step must have step_number, action, and expected_result fields."""
    result = analyst_agent.run({"test_case": sample_test_case_login})
    for step in result["steps"]:
        assert "step_number" in step, f"Missing step_number in step: {step}"
        assert "action" in step, f"Missing action in step: {step}"
        assert "expected_result" in step, f"Missing expected_result in step: {step}"
        assert isinstance(step["step_number"], int), "step_number must be an int"
        assert isinstance(step["action"], str), "action must be a string"
        assert isinstance(step["expected_result"], str), "expected_result must be a string"


def test_analyst_extracts_preconditions(
    analyst_agent: AnalystAgent, sample_test_case_login: str
) -> None:
    """The output preconditions must be a list."""
    result = analyst_agent.run({"test_case": sample_test_case_login})
    assert "preconditions" in result
    assert isinstance(result["preconditions"], list)


def test_analyst_extracts_assertions(
    analyst_agent: AnalystAgent, sample_test_case_login: str
) -> None:
    """The output assertions must be a non-empty list."""
    result = analyst_agent.run({"test_case": sample_test_case_login})
    assert "assertions" in result
    assert isinstance(result["assertions"], list)
    assert len(result["assertions"]) > 0


def test_analyst_returns_valid_json_structure(
    analyst_agent: AnalystAgent, sample_test_case_login: str
) -> None:
    """The full output must match the expected schema with all required keys."""
    result = analyst_agent.run({"test_case": sample_test_case_login})

    required_keys = {"title", "preconditions", "steps", "assertions", "test_data"}
    assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - result.keys()}"

    assert isinstance(result["title"], str)
    assert isinstance(result["preconditions"], list)
    assert isinstance(result["steps"], list)
    assert isinstance(result["assertions"], list)
    assert isinstance(result["test_data"], dict)


def test_analyst_handles_search_test_case(
    analyst_agent: AnalystAgent, sample_test_case_search: str
) -> None:
    """Structural checks must hold for the search test case fixture too."""
    result = analyst_agent.run({"test_case": sample_test_case_search})

    assert isinstance(result.get("title"), str)
    assert len(result["title"]) > 0

    assert isinstance(result.get("steps"), list)
    assert len(result["steps"]) >= 1

    for step in result["steps"]:
        assert "step_number" in step
        assert "action" in step
        assert "expected_result" in step

    assert isinstance(result.get("preconditions"), list)
    assert isinstance(result.get("assertions"), list)
    assert len(result["assertions"]) > 0
    assert isinstance(result.get("test_data"), dict)
