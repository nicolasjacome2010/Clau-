"""Anthropic (Claude) adapter for `LLMProvider` — the documented fallback
for the "reasoning-creative" tier (docs/ARCHITECTURE.md §2.6: "OpenAI
GPT-5.x (primario), Claude (fallback si OpenAI degrada)"), and §0's
rationale for a multi-provider gateway in the first place: a pricing
change, an outage, or an aggressive rate limit on one vendor must never
take the whole Reality Engine down.

Anthropic has no direct analogue of OpenAI's `response_format=json_schema`,
so this uses Claude's own recommended pattern for schema-constrained
output: a single tool named after `response_model`, with `tool_choice`
forced to that tool, so the model's reply is always a `tool_use` block
whose `input` already matches the schema — never free-form text to parse.

Requires `ANTHROPIC_API_KEY` to actually call the API — this adapter's own
request/response handling is covered by `tests/unit/ai_gateway/
test_anthropic_provider.py` against a mocked client, since this sandbox
has no API key to test the real network path against (same posture as
`openai_provider.py`).
"""

from __future__ import annotations

from typing import TypeVar

from anthropic import AnthropicError, AsyncAnthropic
from anthropic.types import ToolUseBlock
from pydantic import BaseModel, ValidationError

from reality_engine.ai_gateway.domain.ports import LLMGenerationError, LLMProvider

T = TypeVar("T", bound=BaseModel)


class AnthropicProvider(LLMProvider):
    def __init__(self, client: AsyncAnthropic, *, model: str, max_tokens: int = 4096) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def generate_structured(
        self, *, system_prompt: str, user_input: str, response_model: type[T]
    ) -> T:
        tool_name = response_model.__name__
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_input}],
                tools=[
                    {
                        "name": tool_name,
                        "description": f"Emite un {tool_name} valido segun el esquema dado.",
                        "input_schema": response_model.model_json_schema(),
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
            )
        except AnthropicError as exc:
            raise LLMGenerationError(f"Anthropic request failed: {exc}") from exc

        tool_use = next(
            (block for block in response.content if isinstance(block, ToolUseBlock)), None
        )
        if tool_use is None:
            raise LLMGenerationError("Anthropic response had no tool_use block")

        try:
            return response_model.model_validate(tool_use.input)
        except ValidationError as exc:
            raise LLMGenerationError(f"Anthropic response failed schema validation: {exc}") from exc
