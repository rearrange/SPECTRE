"""GitAgent stub — Phase 4 placeholder; full implementation in Phase 7."""

import logging
from typing import Any, override

from agent_base import BaseAgent
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GitAgent(BaseAgent):
    """Stub git agent that returns a placeholder dict.

    To be replaced in Phase 7 with an agent that branches, commits, pushes
    the generated script, and opens an MR/PR in the target repository.
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        logger.info("[%s] STUB — returning placeholder dict (Phase 4)", self._name)
        return {"branch": None, "commit_sha": None, "pr_url": None, "status": "stub"}
