"""OpenAI adapter for `LLMProvider` — the primary provider per
docs/ARCHITECTURE.md §2.6. Uses Structured Outputs (JSON Schema response
format) so the model's output is validated against `response_model`
server-side before it ever reaches us, then we validate it again locally
with Pydantic as a second line of defense.

Requires `OPENAI_API_KEY` to actually call the API — this adapter's own
request/response handling is covered by `tests/unit/ai_gateway/
test_openai_provider.py` against a mocked client, since this sandbox has
no API key to test the real network path against.
"""

from __future__ import annotations

from typing import TypeVar

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from reality_engine.ai_gateway.domain.ports import LLMGenerationError, LLMProvider

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    def __init__(self, client: AsyncOpenAI, *, model: str) -> None:
        self._client = client
        self._model = model

    async def generate_structured(
        self, *, system_prompt: str, user_input: str, response_model: type[T]
    ) -> T:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_model.__name__,
                        "schema": response_model.model_json_schema(),
                        "strict": True,
                    },
                },
            )
        except OpenAIError as exc:
            raise LLMGenerationError(f"OpenAI request failed: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise LLMGenerationError("OpenAI response had no content")

        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            raise LLMGenerationError(f"OpenAI response failed schema validation: {exc}") from exc
