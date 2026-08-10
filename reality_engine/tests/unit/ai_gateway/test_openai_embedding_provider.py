"""Tests the OpenAI embedding adapter against a mocked `AsyncOpenAI`
client — no network call, no API key needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai import APIError

from reality_engine.ai_gateway.domain.ports import EmbeddingGenerationError
from reality_engine.ai_gateway.infrastructure.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)


def _mock_client(embedding: list[float] | None) -> AsyncMock:
    client = AsyncMock()
    data = [SimpleNamespace(embedding=embedding)] if embedding is not None else []
    response = SimpleNamespace(data=data)
    client.embeddings.create = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_returns_embedding_from_response() -> None:
    client = _mock_client([0.1, 0.2, 0.3])
    provider = OpenAIEmbeddingProvider(client, model="text-embedding-3-small")

    result = await provider.embed("resumen")

    assert result == [0.1, 0.2, 0.3]
    call_kwargs = client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["input"] == "resumen"


@pytest.mark.asyncio
async def test_raises_when_response_has_no_data() -> None:
    client = _mock_client(None)
    provider = OpenAIEmbeddingProvider(client, model="text-embedding-3-small")

    with pytest.raises(EmbeddingGenerationError):
        await provider.embed("resumen")


@pytest.mark.asyncio
async def test_wraps_openai_api_errors() -> None:
    client = AsyncMock()
    client.embeddings.create = AsyncMock(
        side_effect=APIError("boom", request=SimpleNamespace(), body=None)
    )
    provider = OpenAIEmbeddingProvider(client, model="text-embedding-3-small")

    with pytest.raises(EmbeddingGenerationError):
        await provider.embed("resumen")
