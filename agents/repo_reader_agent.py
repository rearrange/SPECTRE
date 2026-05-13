"""RepoReaderAgent stub — Phase 4 placeholder; full implementation in Phase 6."""

import logging
from typing import Any, override

from agent_base import BaseAgent
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class RepoReaderAgent(BaseAgent):
    """Stub repo reader that returns a placeholder dict.

    To be replaced in Phase 6 with an agent that clones or reads an existing
    repository and extracts its structure, test setup, and relevant config
    for Flow A.
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        logger.info("[%s] STUB — returning placeholder dict (Phase 4)", self._name)
        return {"repo_url": input.get("repo_url"), "structure": None, "status": "stub"}
