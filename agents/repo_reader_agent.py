"""RepoReaderAgent — Phase 6: clones a Git repo and extracts structured context."""

import contextlib
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override
from urllib.parse import urlparse

import git

from agent_base import BaseAgent
from errors import RepoReaderError
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_CLONE_BASE = Path(__file__).parent.parent / "output" / "cloned_repos"

_EXCLUDED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".cache", "dist", "build"}
_HELPER_DIRS = {"helpers", "utils", "fixtures", "support"}
_SPEC_SUFFIXES = (".spec.ts", ".test.ts", ".spec.js", ".test.js")

_CYPRESS_SYSTEM_PROMPT = (
    "You are a test migration expert. Given a Cypress test project, produce a concise but "
    "comprehensive mapping guide (plain text, no markdown) that helps a developer convert "
    "Cypress patterns to their Playwright TypeScript equivalents. Cover: navigation, "
    "assertions, element selection, network mocking, and hooks."
)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class RepoContext:
    folder_structure: dict[str, Any]
    naming_conventions: dict[str, str]
    test_patterns: list[dict[str, str]]
    playwright_config: str | None
    tsconfig: str | None
    package_json: str | None
    helper_utilities: list[str]
    is_cypress_repo: bool
    cypress_to_playwright_notes: str | None
    tests_directory: str
    clone_path: str


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class RepoReaderAgent(BaseAgent):
    """Clones an existing Git repo and extracts structured context for downstream agents.

    The only LLM call is for `cypress_to_playwright_notes` when `is_cypress_repo` is True.
    All other analysis is pure filesystem traversal.

    The clone is persisted under `_clone_base/{repo_name}/` and survives after `run()` returns.
    Re-running with the same URL is idempotent — the existing clone is re-analysed.
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)
        self._clone_base: Path = _DEFAULT_CLONE_BASE

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        repo_url: str = input["repo_url"]
        repo_name = _repo_name_from_url(repo_url)
        clone_path = self._clone_base / repo_name

        if clone_path.exists():
            logger.info("[%s] Clone already exists at %s — skipping clone", self._name, clone_path)
        else:
            logger.info("[%s] Cloning %s → %s", self._name, repo_url, clone_path)
            self._clone_base.mkdir(parents=True, exist_ok=True)
            try:
                git.Repo.clone_from(repo_url, clone_path)
            except git.GitCommandError as exc:
                raise RepoReaderError(f"Failed to clone repository '{repo_url}': {exc}") from exc
            except Exception as exc:
                raise RepoReaderError(f"Unexpected error cloning '{repo_url}': {exc}") from exc

        logger.info("[%s] Analysing clone at %s", self._name, clone_path)
        context = self._analyse(clone_path)
        return {
            "folder_structure": context.folder_structure,
            "naming_conventions": context.naming_conventions,
            "test_patterns": context.test_patterns,
            "playwright_config": context.playwright_config,
            "tsconfig": context.tsconfig,
            "package_json": context.package_json,
            "helper_utilities": context.helper_utilities,
            "is_cypress_repo": context.is_cypress_repo,
            "cypress_to_playwright_notes": context.cypress_to_playwright_notes,
            "tests_directory": context.tests_directory,
            "clone_path": context.clone_path,
        }

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def _analyse(self, root: Path) -> RepoContext:
        test_files = _find_test_files(root)
        is_cypress = _is_cypress_repo(root)

        cypress_notes: str | None = None
        if is_cypress:
            cypress_notes = self._generate_cypress_notes(root)

        return RepoContext(
            folder_structure=_build_folder_structure(root),
            naming_conventions=_detect_naming_conventions(test_files),
            test_patterns=_extract_test_patterns(test_files),
            playwright_config=_read_file_if_exists(root / "playwright.config.ts")
            or _read_file_if_exists(root / "playwright.config.js"),
            tsconfig=_read_file_if_exists(root / "tsconfig.json"),
            package_json=_read_file_if_exists(root / "package.json"),
            helper_utilities=_find_helper_utilities(root),
            is_cypress_repo=is_cypress,
            cypress_to_playwright_notes=cypress_notes,
            tests_directory=_detect_tests_directory(root, test_files),
            clone_path=str(root),
        )

    def _generate_cypress_notes(self, root: Path) -> str:
        sample_files: list[str] = []
        for p in root.rglob("*.cy.ts"):
            sample_files.append(p.read_text()[:2000])
            if len(sample_files) >= 2:
                break

        user_message = (
            "Convert the following Cypress test patterns to Playwright TypeScript equivalents.\n\n"
            "Sample Cypress files:\n"
            + "\n---\n".join(sample_files)
            + "\n\nProvide a concise mapping guide (plain text only)."
        )
        observation = self._react_loop(user_message)
        response = self._llm.complete(system=_CYPRESS_SYSTEM_PROMPT, user=observation)
        return response.content.strip()


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _repo_name_from_url(url: str) -> str:
    """Derive a short repo name from a URL or local path."""
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https", "git", "ssh"):
        name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    else:
        name = Path(url).name
    return name.removesuffix(".git") or "repo"


def _build_folder_structure(root: Path, max_depth: int = 4) -> dict[str, Any]:
    def _traverse(path: Path, depth: int) -> dict[str, Any]:
        if depth > max_depth:
            return {}
        result: dict[str, Any] = {}
        try:
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return {}
        for item in items:
            if item.name in _EXCLUDED_DIRS:
                continue
            if item.is_dir():
                result[item.name + "/"] = _traverse(item, depth + 1)
            else:
                result[item.name] = None
        return result

    return _traverse(root, 0)


def _find_test_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for suffix in _SPEC_SUFFIXES:
        files.extend(root.rglob(f"*{suffix}"))
    return sorted(files)


def _extract_test_patterns(test_files: list[Path]) -> list[dict[str, str]]:
    patterns: list[dict[str, str]] = []
    for f in test_files[:3]:
        lines = f.read_text(errors="replace").splitlines()[:50]
        patterns.append({"file": str(f.name), "content": "\n".join(lines)})
    return patterns


def _detect_naming_conventions(test_files: list[Path]) -> dict[str, str]:
    if not test_files:
        return {"file_naming": "unknown", "test_suffix": "unknown"}

    suffix_votes: list[str] = []
    for f in test_files:
        for s in _SPEC_SUFFIXES:
            if f.name.endswith(s):
                suffix_votes.append(s)
                break
    test_suffix = Counter(suffix_votes).most_common(1)[0][0] if suffix_votes else "unknown"

    stems = [re.sub(r"\.(spec|test)\.[jt]s$", "", f.name) for f in test_files]
    kebab = re.compile(r"^[a-z][a-z0-9-]*$")
    camel = re.compile(r"^[a-z][a-zA-Z0-9]+$")
    pascal = re.compile(r"^[A-Z][a-zA-Z0-9]+$")

    if all(kebab.match(s) for s in stems):
        file_naming = "kebab-case"
    elif all(camel.match(s) for s in stems):
        file_naming = "camelCase"
    elif all(pascal.match(s) for s in stems):
        file_naming = "PascalCase"
    else:
        file_naming = "mixed"

    return {"file_naming": file_naming, "test_suffix": test_suffix}


def _detect_tests_directory(root: Path, test_files: list[Path]) -> str:
    if not test_files:
        return "tests/"
    dirs: list[str] = []
    for f in test_files:
        try:
            rel = f.relative_to(root)
            dirs.append(str(rel.parts[0]) + "/" if len(rel.parts) > 1 else "")
        except ValueError:
            continue
    if not dirs:
        return "tests/"
    return Counter(dirs).most_common(1)[0][0] or "tests/"


def _find_helper_utilities(root: Path) -> list[str]:
    helpers: list[str] = []
    for d in _HELPER_DIRS:
        target = root / d
        if target.is_dir():
            for f in sorted(target.rglob("*")):
                if f.is_file():
                    with contextlib.suppress(ValueError):
                        helpers.append(str(f.relative_to(root)))
    return helpers


def _is_cypress_repo(root: Path) -> bool:
    cypress_configs = list(root.glob("cypress.config.*"))
    cypress_dir = root / "cypress"
    return bool(cypress_configs) or cypress_dir.is_dir()


def _read_file_if_exists(path: Path) -> str | None:
    if path.is_file():
        return path.read_text(errors="replace")
    return None
