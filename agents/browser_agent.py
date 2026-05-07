"""BrowserAgent — navigates a web page and returns structured JSON observations."""

import json
import logging
from typing import Any, override

from playwright.async_api import Page

from agent_base import BaseAgent
from llm.base import LLMProvider
from tools.browser_tools import (
    browse_url,
    get_interactive_elements,
    get_page_title,
    take_screenshot,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert web analyst. You will be given a URL, page title, interactive elements, and raw HTML content from a web page.

Analyze the page and return a single valid JSON object — no markdown, no code fences, no preamble, no trailing text. Only output the JSON object.

The JSON must have exactly these top-level keys:
- "url": string — the URL of the page (copy verbatim from the input)
- "page_title": string — the page title (copy verbatim from the input)
- "interactive_elements": array of objects, each with keys: type (string), label (string), selector (string), placeholder (string or null)
- "forms": array of objects describing HTML forms (use empty array [] if no explicit form elements are found)
- "navigation": object with:
    - "links": array of strings (href values of anchor links found on the page)
    - "current_path": string (the path portion of the current URL, e.g. "/" or "/todomvc")
- "page_structure": string — one paragraph describing the overall UI layout and purpose of the page

Return ONLY the JSON object. No explanation, no markdown, no code fences."""


class BrowserParseError(Exception):
    """Raised when the LLM response cannot be parsed as valid JSON."""


class BrowserAgent(BaseAgent):
    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Navigate to a URL and return structured JSON observations.

        Args:
            input: dict with keys "url" (str) and "page" (Playwright Page).

        Returns:
            Parsed dict matching the browser agent output schema.

        Raises:
            BrowserParseError: if the LLM response is not valid JSON.
        """
        url: str = input["url"]
        page: Page = input["page"]

        logger.info("[%s] Running — url: %s", self._name, url)

        # THINK
        _ = self._think(f"Analyzing page at {url}")

        # ACT: gather raw observations using browser tools
        html_content = await browse_url(page, url)
        page_title = await get_page_title(page)
        interactive_elements = await get_interactive_elements(page)
        await take_screenshot(page, "initial")

        # OBSERVE: build the message for the LLM (truncate HTML to stay within token budget)
        truncated_html = html_content[:8000]
        raw_observations = f"URL: {url}\nTitle: {page_title}\nHTML:\n{truncated_html}"

        user_message = (
            f"URL: {url}\n"
            f"Page Title: {page_title}\n"
            f"Interactive Elements:\n{json.dumps(interactive_elements, indent=2)}\n"
            f"Raw HTML (first 8000 chars):\n{truncated_html}"
        )

        observation = self._observe(user_message)
        response = self._llm.complete(system=SYSTEM_PROMPT, user=observation)

        logger.info(
            "[%s] LLM responded — model=%s in=%d out=%d",
            self._name,
            response.model,
            response.input_tokens,
            response.output_tokens,
        )

        raw_content = response.content.strip()
        try:
            result: dict[str, Any] = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise BrowserParseError(raw_content) from exc

        # Agent sets raw_observations directly — the LLM does not echo back the full HTML
        result["raw_observations"] = raw_observations

        return result
