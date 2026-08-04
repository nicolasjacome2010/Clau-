from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.memory.application.use_cases import (
    FindSimilarMemoriesInput,
    FindSimilarMemoriesUseCase,
    GetUserBiasProfileUseCase,
    ListMemoriesForUserUseCase,
    RecordBiasObservationInput,
    RecordBiasObservationUseCase,
    RecordCalibrationInput,
    RecordCalibrationUseCase,
    StoreMemoryInput,
    StoreMemoryUseCase,
)
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.memory.fakes import (
    InMemoryMemoryEmbeddingRepository,
    InMemoryUserBiasProfileRepository,
)


@pytest.mark.asyncio
async def test_get_bias_profile_returns_empty_default_when_none_recorded() -> None:
    profiles = InMemoryUserBiasProfileRepository()
    user_id = uuid4()

    profile = await GetUserBiasProfileUseCase(profiles).execute(user_id)

    assert profile.user_id == user_id
    assert profile.biases == ()
    assert profile.calibration_score == 0.0


@pytest.mark.asyncio
async def test_record_bias_observation_persists_incremental_update() -> None:
    profiles = InMemoryUserBiasProfileRepository()
    user_id = uuid4()
    use_case = RecordBiasObservationUseCase(profiles)

    await use_case.execute(
        RecordBiasObservationInput(user_id=user_id, bias="loss_aversion", confidence=0.6)
    )
    updated = await use_case.execute(
        RecordBiasObservationInput(user_id=user_id, bias="loss_aversion", confidence=0.8)
    )

    assert len(updated.biases) == 1
    assert updated.biases[0].occurrences == 2
    persisted = await profiles.get_by_user_id(user_id)
    assert persisted == updated


@pytest.mark.asyncio
async def test_record_calibration_persists_update() -> None:
    profiles = InMemoryUserBiasProfileRepository()
    user_id = uuid4()

    updated = await RecordCalibrationUseCase(profiles).execute(
        RecordCalibrationInput(user_id=user_id, calibration_delta=90.0)
    )

    assert updated.calibration_score == pytest.approx(18.0)  # 0*0.8 + 90*0.2


async def _make_decision(decisions: InMemoryDecisionRepository, user_id: object) -> Decision:
    now = datetime.now(UTC)
    return await decisions.create(
        Decision(
            id=uuid4(),
            user_id=user_id,  # type: ignore[arg-type]
            title="t",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.DRAFT,
            raw_input="algo",
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_store_memory_creates_new_entry() -> None:
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    decision = await _make_decision(decisions, user_id)

    memory = await StoreMemoryUseCase(memories, decisions).execute(
        StoreMemoryInput(
            user_id=user_id,
            summary_text="resumen de la decisión",
            embedding=(1.0, 0.0, 0.0),
            decision_id=decision.id,
        )
    )

    assert memory.decision_id == decision.id
    stored = await memories.list_for_user(user_id)
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_store_memory_raises_when_decision_not_owned() -> None:
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    owner_id = uuid4()
    decision = await _make_decision(decisions, owner_id)

    with pytest.raises(DecisionNotFoundError):
        await StoreMemoryUseCase(memories, decisions).execute(
            StoreMemoryInput(
                user_id=uuid4(),
                summary_text="x",
                embedding=(1.0, 0.0),
                decision_id=decision.id,
            )
        )


@pytest.mark.asyncio
async def test_store_memory_deduplicates_near_identical_embedding() -> None:
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    use_case = StoreMemoryUseCase(memories, decisions)

    first = await use_case.execute(
        StoreMemoryInput(user_id=user_id, summary_text="original", embedding=(1.0, 0.0, 0.0))
    )
    second = await use_case.execute(
        StoreMemoryInput(
            user_id=user_id, summary_text="casi idéntico", embedding=(0.999, 0.001, 0.0)
        )
    )

    assert second.id == first.id
    assert len(await memories.list_for_user(user_id)) == 1


@pytest.mark.asyncio
async def test_store_memory_does_not_deduplicate_dissimilar_embedding() -> None:
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    use_case = StoreMemoryUseCase(memories, decisions)

    await use_case.execute(
        StoreMemoryInput(user_id=user_id, summary_text="a", embedding=(1.0, 0.0, 0.0))
    )
    await use_case.execute(
        StoreMemoryInput(user_id=user_id, summary_text="b", embedding=(0.0, 1.0, 0.0))
    )

    assert len(await memories.list_for_user(user_id)) == 2


@pytest.mark.asyncio
async def test_list_memories_scoped_to_user() -> None:
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    other_user_id = uuid4()
    use_case = StoreMemoryUseCase(memories, decisions)
    await use_case.execute(
        StoreMemoryInput(user_id=user_id, summary_text="mío", embedding=(1.0, 0.0))
    )
    await use_case.execute(
        StoreMemoryInput(user_id=other_user_id, summary_text="de otro", embedding=(1.0, 0.0))
    )

    result = await ListMemoriesForUserUseCase(memories).execute(user_id)

    assert len(result) == 1
    assert result[0].summary_text == "mío"


@pytest.mark.asyncio
async def test_find_similar_ranks_by_cosine_similarity() -> None:
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    use_case = StoreMemoryUseCase(memories, decisions)
    close = await use_case.execute(
        StoreMemoryInput(user_id=user_id, summary_text="cercano", embedding=(0.9, 0.1))
    )
    await use_case.execute(
        StoreMemoryInput(user_id=user_id, summary_text="lejano", embedding=(0.0, 1.0))
    )

    results = await FindSimilarMemoriesUseCase(memories).execute(
        FindSimilarMemoriesInput(user_id=user_id, query_embedding=(1.0, 0.0), top_k=1)
    )

    assert len(results) == 1
    assert results[0][0].id == close.id
