"""OpenAI adapter for `EmbeddingProvider`.

Requires `OPENAI_API_KEY` to actually call the API — covered by
`tests/unit/ai_gateway/test_openai_embedding_provider.py` against a mocked
client, same posture as `openai_provider.py`.
"""

from __future__ import annotations

from openai import AsyncOpenAI, OpenAIError

from reality_engine.ai_gateway.domain.ports import EmbeddingGenerationError, EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, client: AsyncOpenAI, *, model: str) -> None:
        self._client = client
        self._model = model

    async def embed(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings.create(model=self._model, input=text)
        except OpenAIError as exc:
            raise EmbeddingGenerationError(f"OpenAI embedding request failed: {exc}") from exc

        if not response.data:
            raise EmbeddingGenerationError("OpenAI embedding response had no data")

        return response.data[0].embedding
