"""Test/dev double for `EmbeddingProvider`. Never used in production."""

from __future__ import annotations

from reality_engine.ai_gateway.domain.ports import EmbeddingGenerationError, EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        responses: list[list[float] | EmbeddingGenerationError] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        if not self._responses:
            raise EmbeddingGenerationError("FakeEmbeddingProvider has no more canned responses")
        result = self._responses.pop(0)
        if isinstance(result, EmbeddingGenerationError):
            raise result
        return result
