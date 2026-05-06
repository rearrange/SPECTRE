"""AnalystAgent — reads a test case document, extracts structure, returns JSON."""

import json
import logging
from typing import Any, override

from agent_base import BaseAgent
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert QA analyst. You will be given a plain-text manual test case document.

Extract the following information and return it as a single valid JSON object — no markdown, no code fences, no preamble, no trailing text. Only output the JSON object.

The JSON must have exactly these top-level keys:
- "title": string — the test case title
- "preconditions": array of strings — each precondition as a separate string
- "steps": array of objects, each with:
    - "step_number": integer
    - "action": string — what the tester does
    - "expected_result": string — what should happen
- "assertions": array of strings — each assertion/verification point as a separate string
- "test_data": object — key-value pairs of test data mentioned in the document (all values as strings)

If a section is absent from the document, use an empty array [] or empty object {} as appropriate.
Return ONLY the JSON object. No explanation, no markdown."""


class AnalystParseError(Exception):
    """Raised when the LLM response cannot be parsed as valid JSON."""


class AnalystAgent(BaseAgent):
    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Extract structured JSON from a raw plain-text test case.

        Args:
            input: dict with key "test_case" containing the raw test case text.

        Returns:
            Parsed dict matching the analyst schema.

        Raises:
            AnalystParseError: if the LLM response is not valid JSON.
        """
        raw_test_case = input["test_case"]
        logger.info("[%s] Running — test case length: %d chars", self._name, len(raw_test_case))

        observation = self._react_loop(raw_test_case)
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
            result = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise AnalystParseError(raw_content) from exc

        return result
