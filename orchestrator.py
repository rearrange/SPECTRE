"""Orchestrator — Phase 4: full pipeline with flow routing and reviewer retry hook."""

import argparse
import asyncio
import json
import logging
import re
import tempfile
from typing import Any

from playwright.async_api import async_playwright

from agents.analyst_agent import AnalystAgent
from agents.browser_agent import BrowserAgent
from agents.coder_agent import CoderAgent
from agents.git_agent import GitAgent
from agents.repo_reader_agent import RepoReaderAgent
from agents.reviewer_agent import ReviewerAgent
from agents.scaffold_agent import ScaffoldAgent
from llm.anthropic_provider import AnthropicProvider
from llm.base import LLMProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _slugify(text: str) -> str:
    """Convert the first meaningful line of text into a URL-safe slug."""
    first_line = text.strip().split("\n")[0]
    for prefix in ("TEST CASE:", "Test Case:", "test case:"):
        first_line = first_line.replace(prefix, "")
    slug = re.sub(r"[^a-z0-9]+", "-", first_line.lower()).strip("-")
    return slug[:50] or "generated-test"


class Orchestrator:
    """Chains all SPECTRE agents with flow routing and a reviewer retry hook.

    Flow A: repo_url is present  — RepoReader → Analyst → Browser → Coder → Reviewer → Git (branch/push/MR)
    Flow B: repo_url is None     — Scaffold   → Analyst → Browser → Coder → Reviewer → Git (init/commit)
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._analyst = AnalystAgent(llm)
        self._browser = BrowserAgent(llm)
        self._coder = CoderAgent(llm)
        self._reviewer = ReviewerAgent(llm)
        self._repo_reader = RepoReaderAgent(llm)
        self._scaffold = ScaffoldAgent(llm)
        self._git = GitAgent(llm)

    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Execute the full pipeline and return a structured result dict."""
        test_case: str = input["test_case"]
        staging_url: str = input["staging_url"]
        repo_url: str | None = input.get("repo_url")
        test_case_name: str = input.get("test_case_name") or _slugify(test_case)

        flow = "A" if repo_url is not None else "B"
        logger.info("Orchestrator — starting Flow %s (repo_url=%s)", flow, repo_url)

        # Flow-specific preamble
        repo_context: dict[str, Any] | None = None
        scaffold_result: dict[str, Any] | None = None

        if flow == "A":
            logger.info("Orchestrator — Flow A: running RepoReaderAgent")
            repo_context = self._repo_reader.run({"repo_url": repo_url})
        else:
            project_name: str = input.get("project_name") or "spectre-project"
            logger.info("Orchestrator — Flow B: running ScaffoldAgent (project=%s)", project_name)
            scaffold_result = self._scaffold.run({"project_name": project_name})

        # Analyst
        logger.info("Orchestrator — running AnalystAgent")
        analyst_input: dict[str, Any] = {"test_case": test_case}
        if repo_context is not None:
            analyst_input["repo_context"] = repo_context
        try:
            analyst_output = self._analyst.run(analyst_input)
        except Exception as exc:
            raise RuntimeError(f"AnalystAgent failed: {exc}") from exc

        # Browser (async agent — run via asyncio.run if no loop is active)
        logger.info("Orchestrator — running BrowserAgent (url=%s)", staging_url)
        try:
            browser_output = self._run_browser(staging_url)
        except Exception as exc:
            raise RuntimeError(f"BrowserAgent failed: {exc}") from exc

        # Coder + Reviewer retry loop
        coder_input: dict[str, Any] = {
            "analyst_output": analyst_output,
            "browser_output": browser_output,
        }
        coder_output: dict[str, Any] = {}
        reviewer_verdict: dict[str, Any] = {}
        retries = 0
        for attempt in range(MAX_RETRIES):
            logger.info("Orchestrator — CoderAgent attempt %d/%d", attempt + 1, MAX_RETRIES)
            try:
                coder_output = self._coder.run(coder_input)
            except Exception as exc:
                raise RuntimeError(f"CoderAgent failed: {exc}") from exc

            logger.info("Orchestrator — ReviewerAgent attempt %d/%d", attempt + 1, MAX_RETRIES)
            reviewer_verdict = self._reviewer.run(
                {"script": coder_output["script"], "analyst_output": analyst_output}
            )
            if reviewer_verdict["verdict"] == "PASS":
                retries = attempt
                break
            retries = attempt
            logger.warning(
                "Orchestrator — reviewer returned FAIL on attempt %d: %s",
                attempt + 1,
                reviewer_verdict.get("issues"),
            )
            coder_input = {
                "analyst_output": analyst_output,
                "browser_output": browser_output,
                "reviewer_feedback": reviewer_verdict,
            }
        else:
            # Loop exhausted without a PASS
            retries = MAX_RETRIES - 1

        # Git agent — save script to a temp file then hand off
        logger.info("Orchestrator — running GitAgent (Flow %s)", flow)
        with tempfile.NamedTemporaryFile(
            suffix=".spec.ts", mode="w", delete=False, prefix=f"spectre-{test_case_name}-"
        ) as tmp:
            tmp.write(coder_output["script"])
            script_path = tmp.name

        repo_path: str = ""
        if flow == "A" and repo_context is not None:
            repo_path = str(repo_context.get("clone_path", ""))
        elif flow == "B" and scaffold_result is not None:
            repo_path = str(scaffold_result.get("project_root", ""))

        git_input: dict[str, Any] = {
            "flow": flow,
            "test_case_name": test_case_name,
            "script_path": script_path,
            "repo_path": repo_path,
        }
        if flow == "A":
            git_input["repo_url"] = repo_url

        git_result = self._git.run(git_input)

        return {
            "flow": flow,
            "analyst_output": analyst_output,
            "browser_output": browser_output,
            "coder_output": coder_output,
            "reviewer_verdict": reviewer_verdict,
            "retries": retries,
            "script": coder_output["script"],
            "repo_context": repo_context,
            "scaffold_result": scaffold_result,
            "git_result": git_result,
        }

    def _run_browser(self, url: str) -> dict[str, Any]:
        """Launch Playwright, drive BrowserAgent, and return observations."""
        return asyncio.run(self._run_browser_async(url))

    async def _run_browser_async(self, url: str) -> dict[str, Any]:
        """Async core: launches Chromium, passes page to BrowserAgent."""
        import inspect

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                result = self._browser.run({"url": url, "page": page})
                if inspect.isawaitable(result):
                    return await result
                return result  # type: ignore[return-value]
            finally:
                await page.close()
                await browser.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SPECTRE orchestrator — run the full pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  Flow B (new project):    orchestrator.py test_case.txt https://staging.example.com\n"
            "  Flow A (existing repo):  orchestrator.py test_case.txt https://staging.example.com https://gitlab.example.com/your/repo"
        ),
    )
    parser.add_argument("test_case_file", help="path to plain-text test case file")
    parser.add_argument("staging_url", help="staging URL to browse")
    parser.add_argument(
        "repo_url", nargs="?", default=None, help="optional repo URL (triggers Flow A)"
    )

    args = parser.parse_args()

    with open(args.test_case_file) as f:
        test_case_text = f.read()

    llm = AnthropicProvider()
    orch = Orchestrator(llm=llm)
    result = orch.run(
        {
            "test_case": test_case_text,
            "staging_url": args.staging_url,
            "repo_url": args.repo_url,
        }
    )

    script = result.pop("script")
    print(json.dumps(result, indent=2))
    print("\n--- Generated .spec.ts ---")
    print(script)
