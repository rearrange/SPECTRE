"""Orchestrator — chains AnalystAgent → BrowserAgent for SPECTRE Phase 2."""

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


async def run(test_case: str, url: str) -> dict[str, Any]:
    """Run the Phase 2 pipeline: Analyst → Browser."""
    llm = AnthropicProvider()
    analyst = AnalystAgent(llm)
    browser_agent = BrowserAgent(llm)

    logger.info("Orchestrator — running Analyst Agent")
    analyst_result = analyst.run({"test_case": test_case})

    logger.info("Orchestrator — running Browser Agent")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            browser_result = await browser_agent.run({"url": url, "page": page})
        finally:
            await page.close()
            await browser.close()

    return {"analyst": analyst_result, "browser": browser_result}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run python orchestrator.py <test_case_file> <staging_url>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        raw = f.read()

    result = asyncio.run(run(raw, sys.argv[2]))
    print(json.dumps(result, indent=2))
