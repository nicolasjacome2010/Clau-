from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.identity.domain.entities import User
from core_api.identity.infrastructure.repository import SqlAlchemyUserRepository
from core_api.memory.domain.entities import BiasObservation, MemoryEmbedding, UserBiasProfile
from core_api.memory.infrastructure.repository import (
    SqlAlchemyMemoryEmbeddingRepository,
    SqlAlchemyUserBiasProfileRepository,
)


async def _make_user(session: AsyncSession) -> User:
    now = datetime.now(UTC)
    return await SqlAlchemyUserRepository(session).create(
        User(
            id=uuid4(),
            email=f"{uuid4()}@example.com",
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_bias_profile_upsert_inserts_then_updates(sqlite_session: AsyncSession) -> None:
    user = await _make_user(sqlite_session)
    repo = SqlAlchemyUserBiasProfileRepository(sqlite_session)
    now = datetime.now(UTC)

    await repo.upsert(
        UserBiasProfile(
            user_id=user.id,
            biases=(BiasObservation(bias="loss_aversion", score=0.5, occurrences=1),),
            calibration_score=10.0,
            updated_at=now,
        )
    )
    updated = await repo.upsert(
        UserBiasProfile(
            user_id=user.id,
            biases=(BiasObservation(bias="loss_aversion", score=0.7, occurrences=2),),
            calibration_score=15.0,
            updated_at=now,
        )
    )
    fetched = await repo.get_by_user_id(user.id)

    assert updated.calibration_score == 15.0
    assert fetched is not None
    assert fetched.biases[0].score == 0.7
    assert fetched.biases[0].occurrences == 2


@pytest.mark.asyncio
async def test_bias_profile_returns_none_when_missing(sqlite_session: AsyncSession) -> None:
    repo = SqlAlchemyUserBiasProfileRepository(sqlite_session)

    assert await repo.get_by_user_id(uuid4()) is None


@pytest.mark.asyncio
async def test_create_and_list_memory_embeddings(sqlite_session: AsyncSession) -> None:
    user = await _make_user(sqlite_session)
    repo = SqlAlchemyMemoryEmbeddingRepository(sqlite_session)
    now = datetime.now(UTC)

    created = await repo.create(
        MemoryEmbedding(
            id=uuid4(),
            user_id=user.id,
            decision_id=None,
            summary_text="resumen",
            embedding=(0.1, 0.2, 0.3),
            created_at=now,
        )
    )
    result = await repo.list_for_user(user.id)

    assert created.summary_text == "resumen"
    assert len(result) == 1
    assert result[0].embedding == (0.1, 0.2, 0.3)


@pytest.mark.asyncio
async def test_find_similar_ranks_by_cosine_similarity(sqlite_session: AsyncSession) -> None:
    user = await _make_user(sqlite_session)
    repo = SqlAlchemyMemoryEmbeddingRepository(sqlite_session)
    now = datetime.now(UTC)

    close = await repo.create(
        MemoryEmbedding(
            id=uuid4(),
            user_id=user.id,
            decision_id=None,
            summary_text="cercano",
            embedding=(0.9, 0.1),
            created_at=now,
        )
    )
    await repo.create(
        MemoryEmbedding(
            id=uuid4(),
            user_id=user.id,
            decision_id=None,
            summary_text="lejano",
            embedding=(0.0, 1.0),
            created_at=now,
        )
    )

    results = await repo.find_similar(user.id, (1.0, 0.0), top_k=1)

    assert len(results) == 1
    assert results[0][0].id == close.id
