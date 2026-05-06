from typing import override

from llm.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    @override
    def complete(self, system: str, user: str) -> LLMResponse:
        raise NotImplementedError("OpenAI provider not yet implemented")
