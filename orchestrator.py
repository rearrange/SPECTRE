"""Orchestrator — Phase 4: full pipeline with flow routing and reviewer retry hook."""

import argparse
import asyncio
import json
import logging
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


class Orchestrator:
    """Chains AnalystAgent → BrowserAgent → CoderAgent with flow routing and a reviewer retry hook.

    Flow A: repo_url is present  — RepoReader stub → Analyst → Browser → Coder → Reviewer stub → Git stub
    Flow B: repo_url is None     — Scaffold stub   → Analyst → Browser → Coder → Reviewer stub → Git stub
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

        flow = "A" if repo_url is not None else "B"
        logger.info("Orchestrator — starting Flow %s (repo_url=%s)", flow, repo_url)

        # Flow-specific preamble stubs
        if flow == "A":
            logger.info("Orchestrator — Flow A: running RepoReaderAgent (stub)")
            self._repo_reader.run({"repo_url": repo_url})
        else:
            logger.info("Orchestrator — Flow B: running ScaffoldAgent (stub)")
            self._scaffold.run({})

        # Analyst
        logger.info("Orchestrator — running AnalystAgent")
        try:
            analyst_output = self._analyst.run({"test_case": test_case})
        except Exception as exc:
            raise RuntimeError(f"AnalystAgent failed: {exc}") from exc

        # Browser (async agent — run via asyncio.run if no loop is active)
        logger.info("Orchestrator — running BrowserAgent (url=%s)", staging_url)
        try:
            browser_output = self._run_browser(staging_url)
        except Exception as exc:
            raise RuntimeError(f"BrowserAgent failed: {exc}") from exc

        # Coder
        logger.info("Orchestrator — running CoderAgent")
        try:
            coder_output = self._coder.run(
                {"analyst_output": analyst_output, "browser_output": browser_output}
            )
        except Exception as exc:
            raise RuntimeError(f"CoderAgent failed: {exc}") from exc

        # Reviewer retry loop (stub always passes; loop is structurally wired for Phase 5)
        reviewer_verdict: dict[str, Any] = {}
        retries = 0
        for attempt in range(MAX_RETRIES):
            logger.info("Orchestrator — ReviewerAgent attempt %d/%d", attempt + 1, MAX_RETRIES)
            reviewer_verdict = self._reviewer.run({"script": coder_output["script"]})
            if reviewer_verdict["verdict"] == "PASS":
                retries = attempt
                break
            retries = attempt
            logger.warning(
                "Orchestrator — reviewer returned FAIL on attempt %d: %s",
                attempt + 1,
                reviewer_verdict.get("issues"),
            )
        else:
            # Loop exhausted without a PASS
            retries = MAX_RETRIES - 1

        # Git stub
        logger.info("Orchestrator — running GitAgent (stub)")
        self._git.run({"script": coder_output["script"]})

        return {
            "flow": flow,
            "analyst_output": analyst_output,
            "browser_output": browser_output,
            "coder_output": coder_output,
            "reviewer_verdict": reviewer_verdict,
            "retries": retries,
            "script": coder_output["script"],
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
