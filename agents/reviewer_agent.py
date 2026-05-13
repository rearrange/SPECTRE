"""ReviewerAgent stub — Phase 4 placeholder; full implementation in Phase 5."""

import logging
from typing import Any, override

from agent_base import BaseAgent
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    """Stub reviewer that always returns a PASS verdict.

    To be replaced in Phase 5 with a real LLM-based code reviewer that
    inspects the generated Playwright TypeScript script and returns structured
    feedback for the retry loop.
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        logger.info("[%s] STUB — returning PASS verdict (Phase 4)", self._name)
        return {"verdict": "PASS", "issues": [], "suggestions": []}
