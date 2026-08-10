"""Test/dev double for `LLMProvider`. Never used in production.

Lets pipeline and gateway tests exercise retry/fallback logic and
schema-validation failure paths without any network call or API key.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from reality_engine.ai_gateway.domain.ports import LLMGenerationError, LLMProvider

T = TypeVar("T", bound=BaseModel)


class FakeLLMProvider(LLMProvider):
    """Returns canned responses from `responses`, in order, one per call.

    Each entry is either a `BaseModel` instance to return, or an
    `LLMGenerationError` instance to raise — lets a single test script both
    successes and failures across a sequence of calls (e.g. "fail twice,
    then succeed" to test retry behavior).
    """

    def __init__(
        self,
        responses: list[BaseModel | LLMGenerationError] | None = None,
        *,
        factory: Callable[[str, str, type[BaseModel]], BaseModel] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._factory = factory
        self.calls: list[tuple[str, str]] = []

    async def generate_structured(
        self, *, system_prompt: str, user_input: str, response_model: type[T]
    ) -> T:
        self.calls.append((system_prompt, user_input))

        if self._responses:
            result = self._responses.pop(0)
            if isinstance(result, LLMGenerationError):
                raise result
            return result  # type: ignore[return-value]

        if self._factory is not None:
            return self._factory(system_prompt, user_input, response_model)  # type: ignore[return-value]

        raise LLMGenerationError("FakeLLMProvider has no more canned responses")
