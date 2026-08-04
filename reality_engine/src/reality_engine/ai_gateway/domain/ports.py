"""AI Gateway port: the abstraction every LLM provider must satisfy.

docs/ARCHITECTURE.md §2.3/§2.6 mandates a provider-agnostic gateway instead
of coupling the pipeline directly to one vendor's SDK — a change in
pricing, an outage, or an aggressive rate limit must never take the whole
Reality Engine down. Concrete providers live in `infrastructure/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelTier(StrEnum):
    """Matches docs/ARCHITECTURE.md §2.6's three tiers of task."""

    REASONING_CREATIVE = "reasoning_creative"
    STRUCTURED_EXTRACTION = "structured_extraction"
    SAFETY_CLASSIFICATION = "safety_classification"


class LLMGenerationError(Exception):
    """Raised for any provider failure: network error, malformed output that
    fails schema validation after the provider's own retries, rate limit,
    etc. Callers (AIGateway) treat this uniformly regardless of cause.
    """


class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self, *, system_prompt: str, user_input: str, response_model: type[T]
    ) -> T:
        """Returns an instance of `response_model`, parsed and validated
        from the provider's output. Raises `LLMGenerationError` if the
        provider cannot produce a valid instance.
        """
        ...
