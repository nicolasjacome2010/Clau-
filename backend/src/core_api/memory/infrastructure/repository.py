"""SQLAlchemy implementations of the memory domain repositories.

`SqlAlchemyMemoryEmbeddingRepository.find_similar` does a linear scan over
every embedding the user has and ranks by cosine similarity in Python —
correct, but O(n) per user. docs/ARCHITECTURE.md §7 documents the actual
migration point: once a user's embedding count or query latency crosses
its stated threshold, this repository swaps its query for a real pgvector
`ORDER BY embedding <=> :query LIMIT :k` (ivfflat/HNSW index) — no change
needed anywhere outside this file, since callers only depend on
`MemoryEmbeddingRepository`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.memory.domain.entities import BiasObservation, MemoryEmbedding, UserBiasProfile
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.memory.domain.similarity import cosine_similarity
from core_api.memory.infrastructure.models import MemoryEmbeddingModel, UserBiasProfileModel


def _to_profile_entity(model: UserBiasProfileModel) -> UserBiasProfile:
    return UserBiasProfile(
        user_id=model.user_id,
        biases=tuple(BiasObservation(**bias) for bias in model.biases),
        calibration_score=float(model.calibration_score),
        updated_at=model.updated_at,
    )


class SqlAlchemyUserBiasProfileRepository(UserBiasProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> UserBiasProfile | None:
        model = await self._session.get(UserBiasProfileModel, user_id)
        return _to_profile_entity(model) if model else None

    async def upsert(self, profile: UserBiasProfile) -> UserBiasProfile:
        biases_json = [
            {"bias": b.bias, "score": b.score, "occurrences": b.occurrences} for b in profile.biases
        ]
        # `UserBiasProfile.updated_at` is optional in the domain (a
        # never-persisted default profile has none), but the column is
        # NOT NULL — persisting always stamps a real timestamp.
        updated_at = profile.updated_at or datetime.now(UTC)
        model = await self._session.get(UserBiasProfileModel, profile.user_id)
        if model is None:
            model = UserBiasProfileModel(
                user_id=profile.user_id,
                biases=biases_json,
                calibration_score=profile.calibration_score,
                updated_at=updated_at,
            )
            self._session.add(model)
        else:
            model.biases = biases_json
            model.calibration_score = profile.calibration_score
            model.updated_at = updated_at
        await self._session.flush()
        return _to_profile_entity(model)


def _to_memory_entity(model: MemoryEmbeddingModel) -> MemoryEmbedding:
    return MemoryEmbedding(
        id=model.id,
        user_id=model.user_id,
        decision_id=model.decision_id,
        summary_text=model.summary_text,
        embedding=tuple(model.embedding),
        created_at=model.created_at,
    )


class SqlAlchemyMemoryEmbeddingRepository(MemoryEmbeddingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: UUID) -> list[MemoryEmbedding]:
        result = await self._session.execute(
            select(MemoryEmbeddingModel)
            .where(MemoryEmbeddingModel.user_id == user_id)
            .order_by(MemoryEmbeddingModel.created_at.desc())
        )
        return [_to_memory_entity(model) for model in result.scalars().all()]

    async def create(self, embedding: MemoryEmbedding) -> MemoryEmbedding:
        model = MemoryEmbeddingModel(
            id=embedding.id,
            user_id=embedding.user_id,
            decision_id=embedding.decision_id,
            summary_text=embedding.summary_text,
            embedding=list(embedding.embedding),
            created_at=embedding.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_memory_entity(model)

    async def find_similar(
        self, user_id: UUID, query_embedding: tuple[float, ...], *, top_k: int = 5
    ) -> list[tuple[MemoryEmbedding, float]]:
        candidates = await self.list_for_user(user_id)
        scored = [
            (memory, cosine_similarity(memory.embedding, query_embedding)) for memory in candidates
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
