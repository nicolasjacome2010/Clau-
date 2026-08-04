"""In-memory fakes for the memory bounded context, used only by unit tests."""

from __future__ import annotations

from uuid import UUID

from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.memory.domain.similarity import cosine_similarity


class InMemoryUserBiasProfileRepository(UserBiasProfileRepository):
    def __init__(self) -> None:
        self._profiles: dict[UUID, UserBiasProfile] = {}

    async def get_by_user_id(self, user_id: UUID) -> UserBiasProfile | None:
        return self._profiles.get(user_id)

    async def upsert(self, profile: UserBiasProfile) -> UserBiasProfile:
        self._profiles[profile.user_id] = profile
        return profile


class InMemoryMemoryEmbeddingRepository(MemoryEmbeddingRepository):
    def __init__(self) -> None:
        self._memories: dict[UUID, MemoryEmbedding] = {}

    async def list_for_user(self, user_id: UUID) -> list[MemoryEmbedding]:
        return [m for m in self._memories.values() if m.user_id == user_id]

    async def create(self, embedding: MemoryEmbedding) -> MemoryEmbedding:
        self._memories[embedding.id] = embedding
        return embedding

    async def find_similar(
        self, user_id: UUID, query_embedding: tuple[float, ...], *, top_k: int = 5
    ) -> list[tuple[MemoryEmbedding, float]]:
        candidates = await self.list_for_user(user_id)
        scored = [
            (memory, cosine_similarity(memory.embedding, query_embedding)) for memory in candidates
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
