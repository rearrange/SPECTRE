"""ReviewerAgent — Phase 5: LLM-based Playwright TypeScript script reviewer."""

import json
import logging
from typing import Any, override

from agent_base import BaseAgent
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict Playwright TypeScript test reviewer. You evaluate generated test scripts for syntax correctness, test coverage completeness, and best practices compliance. You respond only with a JSON object — no explanation, no markdown."""


class ReviewerError(Exception):
    """Raised when the LLM returns an empty or unparseable response."""


class ReviewerAgent(BaseAgent):
    """Reviews a generated Playwright TypeScript script against three criteria:

    1. Playwright TS syntax validity
    2. Test coverage — all steps and assertions from analyst_output are present
    3. Best practices — proper expect() assertions, good locator strategy, no hardcoded sleeps
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        script: str = input["script"]
        analyst_output: dict[str, Any] = input["analyst_output"]

        logger.info("[%s] Reviewing script (%d chars)", self._name, len(script))

        user_message = (
            "Review the following Playwright TypeScript test script against the original test plan.\n\n"
            "[TEST PLAN]\n"
            f"{json.dumps(analyst_output, indent=2)}\n\n"
            "[GENERATED SCRIPT]\n"
            f"{script}\n\n"
            "Respond with a JSON object:\n"
            "{\n"
            '  "verdict": "PASS" or "FAIL",\n'
            '  "issues": ["<specific issue>", ...],\n'
            '  "suggestions": ["<actionable suggestion>", ...]\n'
            "}\n\n"
            "Verdict rules:\n"
            "- PASS: script is syntactically valid, covers all test steps, uses proper assertions and good locator strategy\n"
            "- FAIL: any of the three criteria are violated\n"
            "  1. Playwright TS syntax validity — valid TypeScript, correct Playwright API usage (test(), expect(), page.* calls, proper async/await)\n"
            "  2. Test coverage — every step and assertion from the test plan is represented in the script\n"
            "  3. Best practices — proper expect() assertions (not bare calls), meaningful locator strategy (prefer getByRole, getByLabel, getByTestId over raw CSS/XPath), no page.waitForTimeout() hardcoded sleeps"
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

        content = response.content.strip()
        if not content:
            raise ReviewerError("LLM returned an empty response")

        # Strip markdown code fences the LLM occasionally adds despite instructions
        if content.startswith("```"):
            lines = content.splitlines()
            lines = [line for line in lines if not line.startswith("```")]
            content = "\n".join(lines).strip()

        try:
            result: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ReviewerError(f"LLM returned unparseable JSON: {content!r}") from exc

        logger.info("[%s] Verdict: %s", self._name, result.get("verdict"))
        return result
