"""Repository interfaces (ports) for the memory bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile


class UserBiasProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> UserBiasProfile | None: ...

    @abstractmethod
    async def upsert(self, profile: UserBiasProfile) -> UserBiasProfile: ...


class MemoryEmbeddingRepository(ABC):
    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[MemoryEmbedding]: ...

    @abstractmethod
    async def create(self, embedding: MemoryEmbedding) -> MemoryEmbedding: ...

    @abstractmethod
    async def find_similar(
        self, user_id: UUID, query_embedding: tuple[float, ...], *, top_k: int = 5
    ) -> list[tuple[MemoryEmbedding, float]]:
        """Returns up to `top_k` (MemoryEmbedding, cosine_similarity) pairs
        for the user, most similar first.
        """
        ...
