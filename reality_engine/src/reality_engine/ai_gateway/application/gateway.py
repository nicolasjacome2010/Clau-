"""The AI Gateway: provider selection, retry, and fallback.

docs/ARCHITECTURE.md §2.3: "retries con backoff, fallback entre
proveedores, validación de salida contra JSON Schema". Each `ModelTier` is
configured with an ordered list of providers — the first is primary, the
rest are fallbacks tried only if every retry against the current one is
exhausted (e.g. OpenAI primary, Anthropic fallback for
`REASONING_CREATIVE`, per docs/ARCHITECTURE.md §2.6).

Embeddings get the same retry/fallback treatment as structured generation
(CLAUDE.md: "Never call a model provider's SDK directly from a pipeline
agent") — a single ordered list of `EmbeddingProvider`s, since today there
is realistically one embedding provider, but the shape stays consistent
with the LLM side rather than special-cased.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from reality_engine.ai_gateway.domain.ports import (
    EmbeddingGenerationError,
    EmbeddingProvider,
    LLMGenerationError,
    LLMProvider,
    ModelTier,
)

T = TypeVar("T", bound=BaseModel)


class AIGateway:
    def __init__(
        self,
        providers_by_tier: dict[ModelTier, list[LLMProvider]],
        *,
        retries_per_provider: int = 1,
        embedding_providers: list[EmbeddingProvider] | None = None,
    ) -> None:
        self._providers_by_tier = providers_by_tier
        self._retries_per_provider = retries_per_provider
        self._embedding_providers = embedding_providers or []

    async def generate_structured(
        self,
        *,
        tier: ModelTier,
        system_prompt: str,
        user_input: str,
        response_model: type[T],
    ) -> T:
        providers = self._providers_by_tier.get(tier, [])
        if not providers:
            raise LLMGenerationError(f"No provider configured for tier '{tier.value}'")

        last_error: Exception | None = None
        for provider in providers:
            for _attempt in range(self._retries_per_provider + 1):
                try:
                    return await provider.generate_structured(
                        system_prompt=system_prompt,
                        user_input=user_input,
                        response_model=response_model,
                    )
                except LLMGenerationError as exc:
                    last_error = exc
                    continue

        raise LLMGenerationError(
            f"All providers exhausted for tier '{tier.value}'"
        ) from last_error

    async def embed(self, text: str) -> list[float]:
        if not self._embedding_providers:
            raise EmbeddingGenerationError("No embedding provider configured")

        last_error: Exception | None = None
        for provider in self._embedding_providers:
            for _attempt in range(self._retries_per_provider + 1):
                try:
                    return await provider.embed(text)
                except EmbeddingGenerationError as exc:
                    last_error = exc
                    continue

        raise EmbeddingGenerationError("All embedding providers exhausted") from last_error
