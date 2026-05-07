"""Orchestrator — chains AnalystAgent → BrowserAgent for SPECTRE Phase 2."""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from playwright.async_api import async_playwright

from agents.analyst_agent import AnalystAgent
from agents.browser_agent import BrowserAgent
from llm.anthropic_provider import AnthropicProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def run_analyst(test_case: str) -> dict[str, Any]:
    """Run only the Analyst Agent on a test case document."""
    llm = AnthropicProvider()
    analyst = AnalystAgent(llm)
    logger.info("Orchestrator — running Analyst Agent")
    return analyst.run({"test_case": test_case})


async def run_browser(url: str) -> dict[str, Any]:
    """Run only the Browser Agent on a URL."""
    llm = AnthropicProvider()
    browser_agent = BrowserAgent(llm)
    logger.info("Orchestrator — running Browser Agent")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            return await browser_agent.run({"url": url, "page": page})
        finally:
            await page.close()
            await browser.close()


async def run(test_case: str, url: str) -> dict[str, Any]:
    """Run the full pipeline: Analyst → Browser."""
    analyst_result = run_analyst(test_case)
    browser_result = await run_browser(url)
    return {"analyst": analyst_result, "browser": browser_result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SPECTRE orchestrator — run the full pipeline or a single agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  full pipeline:   orchestrator.py test_case.txt https://example.com\n"
            "  analyst only:    orchestrator.py --analyst-only test_case.txt\n"
            "  browser only:    orchestrator.py --browser-only https://example.com"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--analyst-only",
        metavar="FILE",
        help="run only the Analyst Agent on FILE",
    )
    mode.add_argument(
        "--browser-only",
        metavar="URL",
        help="run only the Browser Agent on URL",
    )
    parser.add_argument("test_case_file", nargs="?", help="test case file (full pipeline)")
    parser.add_argument("url", nargs="?", help="target URL (full pipeline)")

    args = parser.parse_args()

    if args.analyst_only:
        with open(args.analyst_only) as f:
            raw = f.read()
        result = run_analyst(raw)
    elif args.browser_only:
        result = asyncio.run(run_browser(args.browser_only))
    elif args.test_case_file and args.url:
        with open(args.test_case_file) as f:
            raw = f.read()
        result = asyncio.run(run(raw, args.url))
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))
