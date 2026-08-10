"""Tests the OpenAI adapter's own request/response handling against a
mocked `AsyncOpenAI` client — no network call, no API key needed. What we
verify is *our* code: prompt wiring, JSON parsing, and error mapping.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai import APIError
from pydantic import BaseModel

from reality_engine.ai_gateway.domain.ports import LLMGenerationError
from reality_engine.ai_gateway.infrastructure.openai_provider import OpenAIProvider


class _Classification(BaseModel):
    label: str
    confidence: float


def _mock_client(content: str | None) -> AsyncMock:
    client = AsyncMock()
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_parses_and_validates_successful_response() -> None:
    client = _mock_client('{"label": "none", "confidence": 0.9}')
    provider = OpenAIProvider(client, model="gpt-5-mini")

    result = await provider.generate_structured(
        system_prompt="sys", user_input="hola", response_model=_Classification
    )

    assert result.label == "none"
    assert result.confidence == 0.9
    call_kwargs = client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-5-mini"
    assert call_kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert call_kwargs["messages"][1] == {"role": "user", "content": "hola"}
    assert call_kwargs["response_format"]["json_schema"]["name"] == "_Classification"


@pytest.mark.asyncio
async def test_raises_generation_error_on_malformed_json() -> None:
    client = _mock_client("not json at all")
    provider = OpenAIProvider(client, model="gpt-5-mini")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )


@pytest.mark.asyncio
async def test_raises_generation_error_on_schema_mismatch() -> None:
    client = _mock_client('{"unexpected": "shape"}')
    provider = OpenAIProvider(client, model="gpt-5-mini")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )


@pytest.mark.asyncio
async def test_raises_generation_error_on_empty_content() -> None:
    client = _mock_client(None)
    provider = OpenAIProvider(client, model="gpt-5-mini")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )


@pytest.mark.asyncio
async def test_wraps_openai_api_errors() -> None:
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(
        side_effect=APIError("boom", request=SimpleNamespace(), body=None)
    )
    provider = OpenAIProvider(client, model="gpt-5-mini")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )
