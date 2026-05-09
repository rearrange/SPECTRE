"""CoderAgent — takes AnalystAgent + BrowserAgent output, generates a Playwright TypeScript spec."""

import json
import logging
from typing import Any, override

from agent_base import BaseAgent
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert test automation engineer specialising in Playwright TypeScript.

You will be given two JSON objects:
1. ANALYST OUTPUT — a structured test plan extracted from a manual test case document.
2. BROWSER OUTPUT — a UI observation of the target web application.

Generate a complete, runnable Playwright TypeScript .spec.ts file. Follow these rules exactly:

IMPORTS
- Use exactly: import { test, expect } from '@playwright/test';

STRUCTURE
- Wrap all tests in a single test.describe() block named after the test case title.
- Each test.describe() block contains one or more test() functions.
- Add a descriptive comment above each test() block explaining what it verifies.

AAA PATTERN
- Structure each test with these exact comments marking the sections:
  // Arrange
  // Act
  // Assert

SELECTORS — use in this priority order:
1. data-testid attributes: page.getByTestId('...')
2. Role-based: page.getByRole('...'), page.getByLabel('...'), page.getByPlaceholder('...')
3. Text-based: page.getByText('...')
4. CSS class selectors from the browser observation (last resort only)
5. NEVER use positional selectors: nth-child, nth-of-type, :nth()

STEP COVERAGE
- Each step from the analyst output maps to one or more `await page.*` calls.
- Each assertion from the analyst output maps to an `expect(...)` call.
- Include a page.goto() call using the app_url from test_data.

OUTPUT
- Return ONLY the TypeScript code — no markdown fences, no triple backticks, no preamble, no explanation.
- The output must start with the import statement and end with the closing brace of the describe block."""


class CoderError(Exception):
    """Raised when the LLM returns an empty response."""


class CoderAgent(BaseAgent):
    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Generate a Playwright TypeScript spec from analyst and browser outputs.

        Args:
            input: dict with keys "analyst_output" and "browser_output".

        Returns:
            dict with key "script" containing the TypeScript source as a string.

        Raises:
            CoderError: if the LLM returns an empty response.
        """
        analyst_output: dict[str, Any] = input["analyst_output"]
        browser_output: dict[str, Any] = input["browser_output"]

        logger.info(
            "[%s] Running — test: %s, url: %s",
            self._name,
            analyst_output.get("title", "unknown"),
            browser_output.get("url", "unknown"),
        )

        user_message = (
            "ANALYST OUTPUT:\n"
            f"{json.dumps(analyst_output, indent=2)}\n\n"
            "BROWSER OUTPUT:\n"
            f"{json.dumps(browser_output, indent=2)}"
        )

        observation = self._react_loop(user_message)
        response = self._llm.complete(system=SYSTEM_PROMPT, user=observation)

        logger.info(
            "[%s] LLM responded — model=%s in=%d out=%d",
            self._name,
            response.model,
            response.input_tokens,
            response.output_tokens,
        )

        script = response.content.strip()
        if not script:
            raise CoderError("LLM returned an empty response")

        return {"script": script}
