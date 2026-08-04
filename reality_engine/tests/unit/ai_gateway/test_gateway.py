from __future__ import annotations

import pytest
from pydantic import BaseModel

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider


class _Echo(BaseModel):
    value: str


@pytest.mark.asyncio
async def test_returns_provider_response_on_success() -> None:
    provider = FakeLLMProvider(responses=[_Echo(value="ok")])
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [provider]})

    result = await gateway.generate_structured(
        tier=ModelTier.SAFETY_CLASSIFICATION,
        system_prompt="sys",
        user_input="hola",
        response_model=_Echo,
    )

    assert result.value == "ok"
    assert provider.calls == [("sys", "hola")]


@pytest.mark.asyncio
async def test_retries_same_provider_before_giving_up() -> None:
    provider = FakeLLMProvider(
        responses=[LLMGenerationError("transient"), _Echo(value="recovered")]
    )
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [provider]}, retries_per_provider=1)

    result = await gateway.generate_structured(
        tier=ModelTier.SAFETY_CLASSIFICATION,
        system_prompt="sys",
        user_input="hola",
        response_model=_Echo,
    )

    assert result.value == "recovered"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_falls_back_to_next_provider_when_primary_exhausted() -> None:
    primary = FakeLLMProvider(
        responses=[LLMGenerationError("down"), LLMGenerationError("still down")]
    )
    fallback = FakeLLMProvider(responses=[_Echo(value="from fallback")])
    gateway = AIGateway(
        {ModelTier.REASONING_CREATIVE: [primary, fallback]}, retries_per_provider=1
    )

    result = await gateway.generate_structured(
        tier=ModelTier.REASONING_CREATIVE,
        system_prompt="sys",
        user_input="hola",
        response_model=_Echo,
    )

    assert result.value == "from fallback"
    assert len(primary.calls) == 2
    assert len(fallback.calls) == 1


@pytest.mark.asyncio
async def test_raises_when_all_providers_exhausted() -> None:
    provider = FakeLLMProvider(responses=[LLMGenerationError("down")])
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [provider]}, retries_per_provider=0)

    with pytest.raises(LLMGenerationError):
        await gateway.generate_structured(
            tier=ModelTier.SAFETY_CLASSIFICATION,
            system_prompt="sys",
            user_input="hola",
            response_model=_Echo,
        )


@pytest.mark.asyncio
async def test_raises_when_no_provider_configured_for_tier() -> None:
    gateway = AIGateway({})

    with pytest.raises(LLMGenerationError):
        await gateway.generate_structured(
            tier=ModelTier.REASONING_CREATIVE,
            system_prompt="sys",
            user_input="hola",
            response_model=_Echo,
        )
