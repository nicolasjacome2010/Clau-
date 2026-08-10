from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import EmbeddingGenerationError
from reality_engine.ai_gateway.infrastructure.fake_embedding_provider import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_embed_returns_provider_response_on_success() -> None:
    provider = FakeEmbeddingProvider(responses=[[0.1, 0.2, 0.3]])
    gateway = AIGateway({}, embedding_providers=[provider])

    result = await gateway.embed("resumen de la decisión")

    assert result == [0.1, 0.2, 0.3]
    assert provider.calls == ["resumen de la decisión"]


@pytest.mark.asyncio
async def test_embed_retries_before_giving_up() -> None:
    provider = FakeEmbeddingProvider(
        responses=[EmbeddingGenerationError("transient"), [0.4, 0.5]]
    )
    gateway = AIGateway({}, embedding_providers=[provider], retries_per_provider=1)

    result = await gateway.embed("texto")

    assert result == [0.4, 0.5]
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_embed_falls_back_to_next_provider() -> None:
    primary = FakeEmbeddingProvider(responses=[EmbeddingGenerationError("down")])
    fallback = FakeEmbeddingProvider(responses=[[0.9]])
    gateway = AIGateway({}, embedding_providers=[primary, fallback], retries_per_provider=0)

    result = await gateway.embed("texto")

    assert result == [0.9]


@pytest.mark.asyncio
async def test_embed_raises_when_no_provider_configured() -> None:
    gateway = AIGateway({})

    with pytest.raises(EmbeddingGenerationError):
        await gateway.embed("texto")


@pytest.mark.asyncio
async def test_embed_raises_when_all_providers_exhausted() -> None:
    provider = FakeEmbeddingProvider(responses=[EmbeddingGenerationError("down")])
    gateway = AIGateway({}, embedding_providers=[provider], retries_per_provider=0)

    with pytest.raises(EmbeddingGenerationError):
        await gateway.embed("texto")
