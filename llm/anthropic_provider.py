import os
from typing import override

import anthropic
from anthropic.types import TextBlock
from dotenv import load_dotenv

from llm.base import LLMProvider, LLMResponse

_ = load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048


class AnthropicProvider(LLMProvider):
    _client: anthropic.Anthropic

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    @override
    def complete(self, system: str, user: str) -> LLMResponse:
        message = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text_block = next(
            (block for block in message.content if isinstance(block, TextBlock)),
            None,
        )
        if text_block is None:
            raise ValueError("No text block in Anthropic API response")
        return LLMResponse(
            content=text_block.text,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
