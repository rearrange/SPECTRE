import logging
from abc import ABC, abstractmethod
from typing import Any

from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all SPECTRE agents.

    Implements a ReAct (Reason + Act) loop skeleton:
      think → act → observe → repeat
    """

    _llm: LLMProvider
    _name: str

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._name = self.__class__.__name__

    @abstractmethod
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with the given input and return structured output."""
        ...

    def _think(self, context: str) -> str:
        """Reason about the current context (ReAct: Think step)."""
        logger.info("[%s] THINK — context length: %d chars", self._name, len(context))
        return context

    def _act(self, thought: str) -> str:
        """Take an action based on the thought (ReAct: Act step)."""
        logger.info("[%s] ACT — executing action", self._name)
        return thought

    def _observe(self, result: str) -> str:
        """Observe and process the result of the action (ReAct: Observe step)."""
        logger.info("[%s] OBSERVE — result length: %d chars", self._name, len(result))
        return result

    def _react_loop(self, input_text: str) -> str:
        """Single-iteration ReAct loop skeleton."""
        thought = self._think(input_text)
        action_result = self._act(thought)
        observation = self._observe(action_result)
        return observation
