"""Tests the Anthropic adapter's own request/response handling against a
mocked `AsyncAnthropic` client — no network call, no API key needed. What
we verify is *our* code: tool wiring, tool_choice forcing, and error
mapping — the same posture as `test_openai_provider.py`.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic import APIError
from anthropic.types import ToolUseBlock
from pydantic import BaseModel

from reality_engine.ai_gateway.domain.ports import LLMGenerationError
from reality_engine.ai_gateway.infrastructure.anthropic_provider import AnthropicProvider


class _Classification(BaseModel):
    label: str
    confidence: float


def _tool_use_block(input_dict: dict[str, object]) -> ToolUseBlock:
    return ToolUseBlock(id="tool_1", input=input_dict, name="_Classification", type="tool_use")


def _mock_client(content: list[object]) -> AsyncMock:
    client = AsyncMock()
    response = SimpleNamespace(content=content)
    client.messages.create = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_parses_and_validates_successful_response() -> None:
    client = _mock_client([_tool_use_block({"label": "none", "confidence": 0.9})])
    provider = AnthropicProvider(client, model="claude-opus-5")

    result = await provider.generate_structured(
        system_prompt="sys", user_input="hola", response_model=_Classification
    )

    assert result.label == "none"
    assert result.confidence == 0.9
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-5"
    assert call_kwargs["system"] == "sys"
    assert call_kwargs["messages"] == [{"role": "user", "content": "hola"}]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "_Classification"}
    assert call_kwargs["tools"][0]["name"] == "_Classification"
    assert call_kwargs["tools"][0]["input_schema"] == _Classification.model_json_schema()


@pytest.mark.asyncio
async def test_raises_generation_error_when_no_tool_use_block_present() -> None:
    text_block = SimpleNamespace(type="text", text="no deberia responder texto libre")
    client = _mock_client([text_block])
    provider = AnthropicProvider(client, model="claude-opus-5")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )


@pytest.mark.asyncio
async def test_raises_generation_error_on_schema_mismatch() -> None:
    client = _mock_client([_tool_use_block({"unexpected": "shape"})])
    provider = AnthropicProvider(client, model="claude-opus-5")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )


@pytest.mark.asyncio
async def test_wraps_anthropic_api_errors() -> None:
    client = AsyncMock()
    client.messages.create = AsyncMock(
        side_effect=APIError("boom", request=SimpleNamespace(), body=None)
    )
    provider = AnthropicProvider(client, model="claude-opus-5")

    with pytest.raises(LLMGenerationError):
        await provider.generate_structured(
            system_prompt="sys", user_input="hola", response_model=_Classification
        )
