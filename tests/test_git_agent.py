"""Phase 7 — GitAgent tests.

All tests are Tier 1 (no real git operations, no API calls, no network).
git_tools functions are mocked via unittest.mock.patch.
Filesystem writes use tmp_path where needed.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agents.git_agent import GitAgent
from errors import GitAgentError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def llm() -> MagicMock:
    return MagicMock()


@pytest.fixture
def agent(llm: MagicMock) -> GitAgent:
    return GitAgent(llm)


@pytest.fixture
def script_file(tmp_path: Path) -> Path:
    f = tmp_path / "tc-add-todo.spec.ts"
    f.write_text("import { test, expect } from '@playwright/test';")
    return f


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    return d


def _flow_a_input(script_file: Path, repo_dir: Path) -> dict[str, Any]:
    return {
        "flow": "A",
        "test_case_name": "add-todo",
        "script_path": str(script_file),
        "repo_path": str(repo_dir),
        "repo_url": "https://gitlab.com/example/my-repo",
    }


def _flow_b_input(script_file: Path, repo_dir: Path) -> dict[str, Any]:
    return {
        "flow": "B",
        "test_case_name": "add-todo",
        "script_path": str(script_file),
        "repo_path": str(repo_dir),
    }


# ---------------------------------------------------------------------------
# Flow A — happy path
# ---------------------------------------------------------------------------


def test_flow_a_returns_expected_keys(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.git.Repo", return_value=mock_repo),
        patch("agents.git_agent.create_branch"),
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="deadbeef"),
        patch("agents.git_agent.push_branch"),
        patch(
            "agents.git_agent.open_gitlab_mr",
            return_value="https://gitlab.com/example/my-repo/-/merge_requests/1",
        ),
    ):
        result = agent.run(_flow_a_input(script_file, repo_dir))

    assert set(result.keys()) == {"branch", "commit_sha", "mr_url", "status"}
    assert result["status"] == "success"


def test_flow_a_creates_correct_branch_name(
    agent: GitAgent, script_file: Path, repo_dir: Path
) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.git.Repo", return_value=mock_repo),
        patch("agents.git_agent.create_branch") as mock_branch,
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="deadbeef"),
        patch("agents.git_agent.push_branch"),
        patch("agents.git_agent.open_gitlab_mr", return_value="https://gitlab.com/mr/1"),
    ):
        result = agent.run(_flow_a_input(script_file, repo_dir))

    assert result["branch"] == "spectre/tc-add-todo"
    mock_branch.assert_called_once_with(mock_repo, "spectre/tc-add-todo")


def test_flow_a_commit_message_format(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.git.Repo", return_value=mock_repo),
        patch("agents.git_agent.create_branch"),
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="deadbeef") as mock_commit,
        patch("agents.git_agent.push_branch"),
        patch("agents.git_agent.open_gitlab_mr", return_value="https://gitlab.com/mr/1"),
    ):
        agent.run(_flow_a_input(script_file, repo_dir))

    commit_msg = mock_commit.call_args[0][1]
    assert "add-todo" in commit_msg
    assert commit_msg.startswith("feat(spectre):")


def test_flow_a_calls_open_mr(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.git.Repo", return_value=mock_repo),
        patch("agents.git_agent.create_branch"),
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="deadbeef"),
        patch("agents.git_agent.push_branch"),
        patch("agents.git_agent.open_gitlab_mr", return_value="https://gitlab.com/mr/1") as mock_mr,
    ):
        result = agent.run(_flow_a_input(script_file, repo_dir))

    mock_mr.assert_called_once_with(
        repo_url="https://gitlab.com/example/my-repo",
        branch_name="spectre/tc-add-todo",
        target_branch="main",
        title="feat(spectre): add generated test for add-todo",
    )
    assert result["mr_url"] == "https://gitlab.com/mr/1"


def test_flow_a_missing_repo_url_raises(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    inp = {
        "flow": "A",
        "test_case_name": "add-todo",
        "script_path": str(script_file),
        "repo_path": str(repo_dir),
        # repo_url deliberately absent
    }
    with pytest.raises(GitAgentError, match="repo_url"):
        agent.run(inp)


# ---------------------------------------------------------------------------
# Flow B — happy path
# ---------------------------------------------------------------------------


def test_flow_b_returns_expected_keys(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.init_repo", return_value=mock_repo),
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="cafebabe"),
    ):
        result = agent.run(_flow_b_input(script_file, repo_dir))

    assert set(result.keys()) == {"branch", "commit_sha", "mr_url", "status"}
    assert result["status"] == "success"


def test_flow_b_mr_url_is_none(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.init_repo", return_value=mock_repo),
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="cafebabe"),
    ):
        result = agent.run(_flow_b_input(script_file, repo_dir))

    assert result["mr_url"] is None


def test_flow_b_inits_repo(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.init_repo", return_value=mock_repo) as mock_init,
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="cafebabe"),
    ):
        agent.run(_flow_b_input(script_file, repo_dir))

    mock_init.assert_called_once_with(str(repo_dir))


def test_flow_b_commit_message_format(agent: GitAgent, script_file: Path, repo_dir: Path) -> None:
    mock_repo = MagicMock()
    with (
        patch("agents.git_agent.init_repo", return_value=mock_repo),
        patch("agents.git_agent.copy_script_to_repo", return_value="tests/tc-add-todo.spec.ts"),
        patch("agents.git_agent.stage_and_commit", return_value="cafebabe") as mock_commit,
    ):
        agent.run(_flow_b_input(script_file, repo_dir))

    commit_msg = mock_commit.call_args[0][1]
    assert "add-todo" in commit_msg
    assert commit_msg.startswith("feat(spectre):")


# ---------------------------------------------------------------------------
# git_tools.py unit tests
# ---------------------------------------------------------------------------


def test_detect_provider_gitlab() -> None:
    from tools.git_tools import detect_provider

    assert detect_provider("https://gitlab.com/group/project") == "gitlab"


def test_detect_provider_github() -> None:
    from tools.git_tools import detect_provider

    assert detect_provider("https://github.com/org/repo") == "github"


def test_detect_provider_unknown() -> None:
    from tools.git_tools import detect_provider

    assert detect_provider("https://bitbucket.org/team/repo") == "unknown"


def test_open_github_pr_raises_not_implemented() -> None:
    from tools.git_tools import open_github_pr

    with pytest.raises(NotImplementedError, match="GitHub PR support not yet implemented"):
        open_github_pr("https://github.com/org/repo", "feature/branch")


def test_open_gitlab_mr_raises_if_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools.git_tools import open_gitlab_mr

    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    with pytest.raises(GitAgentError, match="GITLAB_TOKEN"):
        open_gitlab_mr("https://gitlab.com/group/project", "spectre/tc-add-todo")
