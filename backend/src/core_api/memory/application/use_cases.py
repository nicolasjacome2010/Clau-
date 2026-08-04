"""Application use cases for the memory bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.memory.domain.similarity import cosine_similarity

# docs/REALITY_ENGINE.md §2, Agente 11 error `duplicate_memory_entry`:
# "se fusiona con la entrada existente en vez de duplicar (deduplicación
# por similitud de coseno > 0.92)".
_DEDUP_SIMILARITY_THRESHOLD = 0.92


class GetUserBiasProfileUseCase:
    def __init__(self, profile_repository: UserBiasProfileRepository) -> None:
        self._profiles = profile_repository

    async def execute(self, user_id: UUID) -> UserBiasProfile:
        existing = await self._profiles.get_by_user_id(user_id)
        return existing if existing is not None else UserBiasProfile(user_id=user_id)


@dataclass(frozen=True, slots=True)
class RecordBiasObservationInput:
    user_id: UUID
    bias: str
    confidence: float


class RecordBiasObservationUseCase:
    def __init__(self, profile_repository: UserBiasProfileRepository) -> None:
        self._profiles = profile_repository

    async def execute(self, data: RecordBiasObservationInput) -> UserBiasProfile:
        current = await self._profiles.get_by_user_id(data.user_id)
        if current is None:
            current = UserBiasProfile(user_id=data.user_id)
        updated = current.with_bias_observation(
            data.bias, data.confidence, at=datetime.now(UTC)
        )
        return await self._profiles.upsert(updated)


@dataclass(frozen=True, slots=True)
class RecordCalibrationInput:
    user_id: UUID
    calibration_delta: float


class RecordCalibrationUseCase:
    def __init__(self, profile_repository: UserBiasProfileRepository) -> None:
        self._profiles = profile_repository

    async def execute(self, data: RecordCalibrationInput) -> UserBiasProfile:
        current = await self._profiles.get_by_user_id(data.user_id)
        if current is None:
            current = UserBiasProfile(user_id=data.user_id)
        updated = current.with_calibration_delta(data.calibration_delta, at=datetime.now(UTC))
        return await self._profiles.upsert(updated)


@dataclass(frozen=True, slots=True)
class StoreMemoryInput:
    user_id: UUID
    summary_text: str
    embedding: tuple[float, ...]
    decision_id: UUID | None = None


class StoreMemoryUseCase:
    def __init__(
        self,
        memory_repository: MemoryEmbeddingRepository,
        decision_repository: DecisionRepository,
    ) -> None:
        self._memories = memory_repository
        self._decisions = decision_repository

    async def execute(self, data: StoreMemoryInput) -> MemoryEmbedding:
        if data.decision_id is not None:
            decision = await self._decisions.get_by_id(data.decision_id)
            if decision is None or decision.user_id != data.user_id:
                raise DecisionNotFoundError(data.decision_id)

        existing_memories = await self._memories.list_for_user(data.user_id)
        for existing in existing_memories:
            if cosine_similarity(existing.embedding, data.embedding) > _DEDUP_SIMILARITY_THRESHOLD:
                return existing

        return await self._memories.create(
            MemoryEmbedding(
                id=uuid4(),
                user_id=data.user_id,
                decision_id=data.decision_id,
                summary_text=data.summary_text,
                embedding=data.embedding,
                created_at=datetime.now(UTC),
            )
        )


class ListMemoriesForUserUseCase:
    def __init__(self, memory_repository: MemoryEmbeddingRepository) -> None:
        self._memories = memory_repository

    async def execute(self, user_id: UUID) -> list[MemoryEmbedding]:
        return await self._memories.list_for_user(user_id)


@dataclass(frozen=True, slots=True)
class FindSimilarMemoriesInput:
    user_id: UUID
    query_embedding: tuple[float, ...]
    top_k: int = 5


class FindSimilarMemoriesUseCase:
    def __init__(self, memory_repository: MemoryEmbeddingRepository) -> None:
        self._memories = memory_repository

    async def execute(self, data: FindSimilarMemoriesInput) -> list[tuple[MemoryEmbedding, float]]:
        return await self._memories.find_similar(
            data.user_id, data.query_embedding, top_k=data.top_k
        )
