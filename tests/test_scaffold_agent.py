"""Phase 6 — ScaffoldAgent tests.

All tests are Tier 1 (no API calls, no network).
Output is redirected to tmp_path via agent._output_base.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from agents.scaffold_agent import ScaffoldAgent
from errors import ScaffoldError


@pytest.fixture
def output_base(tmp_path: Path) -> Path:
    base = tmp_path / "scaffolded"
    base.mkdir()
    return base


@pytest.fixture
def agent(output_base: Path) -> ScaffoldAgent:
    a = ScaffoldAgent(MagicMock())
    a._output_base = output_base
    return a


def _run(agent: ScaffoldAgent, project_name: str = "my-project") -> dict[str, Any]:
    return agent.run({"project_name": project_name})


# ---------------------------------------------------------------------------
# Project structure
# ---------------------------------------------------------------------------


def test_scaffold_creates_project_root(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    assert (output_base / "my-project").is_dir()


def test_scaffold_creates_all_expected_files(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    root = output_base / "my-project"
    expected = [
        "tests/e2e/.gitkeep",
        "tests/smoke/.gitkeep",
        "pages/base.page.ts",
        "fixtures/index.ts",
        "helpers/auth.helper.ts",
        "test-data/.gitkeep",
        "playwright.config.ts",
        "tsconfig.json",
        "package.json",
        ".gitignore",
        ".gitlab-ci.yml",
    ]
    for rel in expected:
        assert (root / rel).exists(), f"Expected file not found: {rel}"


def test_scaffold_creates_all_directories(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    root = output_base / "my-project"
    for d in ["tests/e2e", "tests/smoke", "pages", "fixtures", "helpers", "test-data"]:
        assert (root / d).is_dir(), f"Expected directory not found: {d}"


# ---------------------------------------------------------------------------
# File content
# ---------------------------------------------------------------------------


def test_playwright_config_content(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / "playwright.config.ts").read_text()
    assert "BASE_URL" in content
    assert "retries" in content
    assert "chromium" in content


def test_tsconfig_strict_mode(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / "tsconfig.json").read_text()
    data = json.loads(content)
    assert data["compilerOptions"]["strict"] is True


def test_package_json_has_scripts(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / "package.json").read_text()
    data = json.loads(content)
    assert "test" in data["scripts"]
    assert "test:smoke" in data["scripts"]
    assert "test:e2e" in data["scripts"]


def test_package_json_has_playwright_dep(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / "package.json").read_text()
    data = json.loads(content)
    assert "@playwright/test" in data.get("devDependencies", {})


def test_gitignore_excludes_node_modules(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / ".gitignore").read_text()
    assert "node_modules" in content


def test_gitlab_ci_has_test_stage(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / ".gitlab-ci.yml").read_text()
    assert "playwright install" in content
    assert "npm test" in content


def test_base_page_ts_is_valid(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / "pages" / "base.page.ts").read_text()
    assert "abstract class" in content
    assert "abstract navigate" in content


def test_fixtures_index_exports_test(agent: ScaffoldAgent, output_base: Path) -> None:
    _run(agent)
    content = (output_base / "my-project" / "fixtures" / "index.ts").read_text()
    assert "test" in content
    assert "expect" in content


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


def test_result_lists_all_created_files(agent: ScaffoldAgent, output_base: Path) -> None:
    result = _run(agent)
    root = Path(result["project_root"])
    listed = set(result["created_files"])
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    assert listed == actual


def test_duplicate_project_name_raises_error(agent: ScaffoldAgent) -> None:
    _run(agent)
    with pytest.raises(ScaffoldError):
        _run(agent)


# ---------------------------------------------------------------------------
# No LLM
# ---------------------------------------------------------------------------


def test_no_llm_calls_made(output_base: Path) -> None:
    llm = MagicMock()
    agent = ScaffoldAgent(llm)
    agent._output_base = output_base
    _run(agent)
    llm.complete.assert_not_called()
