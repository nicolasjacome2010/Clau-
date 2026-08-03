from __future__ import annotations

from uuid import uuid4

import pytest

from core_api.decisions.application.use_cases import (
    CreateDecisionInput,
    CreateDecisionUseCase,
    GetUserDecisionUseCase,
    ListUserDecisionsUseCase,
    UpdateDecisionStatusInput,
    UpdateDecisionStatusUseCase,
)
from core_api.decisions.domain.entities import (
    DecisionStatus,
    DecisionVertical,
    InvalidStatusTransitionError,
)
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from tests.unit.decisions.fakes import InMemoryDecisionRepository


@pytest.mark.asyncio
async def test_create_decision_derives_title_and_starts_as_draft() -> None:
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()

    decision = await CreateDecisionUseCase(decisions).execute(
        CreateDecisionInput(
            user_id=user_id,
            raw_input="  ¿Debo aceptar la oferta de trabajo en la empresa Z?  ",
            vertical=DecisionVertical.CAREER,
        )
    )

    assert decision.status == DecisionStatus.DRAFT
    assert decision.title == "¿Debo aceptar la oferta de trabajo en la empresa Z?"


@pytest.mark.asyncio
async def test_create_decision_truncates_long_raw_input_for_title() -> None:
    decisions = InMemoryDecisionRepository()
    long_input = "palabra " * 30

    decision = await CreateDecisionUseCase(decisions).execute(
        CreateDecisionInput(
            user_id=uuid4(), raw_input=long_input, vertical=DecisionVertical.FINANCE
        )
    )

    assert len(decision.title) <= 80
    assert decision.title.endswith("…")


@pytest.mark.asyncio
async def test_list_user_decisions_filters_by_status() -> None:
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    use_case = CreateDecisionUseCase(decisions)
    draft = await use_case.execute(
        CreateDecisionInput(user_id=user_id, raw_input="A", vertical=DecisionVertical.CAREER)
    )
    clarifying = await use_case.execute(
        CreateDecisionInput(user_id=user_id, raw_input="B", vertical=DecisionVertical.FINANCE)
    )
    await UpdateDecisionStatusUseCase(decisions).execute(
        UpdateDecisionStatusInput(
            decision_id=clarifying.id,
            requesting_user_id=user_id,
            new_status=DecisionStatus.CLARIFYING,
        )
    )

    all_decisions = await ListUserDecisionsUseCase(decisions).execute(user_id)
    only_drafts = await ListUserDecisionsUseCase(decisions).execute(
        user_id, status=DecisionStatus.DRAFT
    )

    assert len(all_decisions) == 2
    assert [d.id for d in only_drafts] == [draft.id]


@pytest.mark.asyncio
async def test_get_user_decision_raises_for_other_users_decision() -> None:
    decisions = InMemoryDecisionRepository()
    owner_id = uuid4()
    decision = await CreateDecisionUseCase(decisions).execute(
        CreateDecisionInput(user_id=owner_id, raw_input="Privado", vertical=DecisionVertical.CAREER)
    )

    with pytest.raises(DecisionNotFoundError):
        await GetUserDecisionUseCase(decisions).execute(decision.id, uuid4())


@pytest.mark.asyncio
async def test_update_status_follows_allowed_transition() -> None:
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    decision = await CreateDecisionUseCase(decisions).execute(
        CreateDecisionInput(user_id=user_id, raw_input="X", vertical=DecisionVertical.CAREER)
    )

    updated = await UpdateDecisionStatusUseCase(decisions).execute(
        UpdateDecisionStatusInput(
            decision_id=decision.id,
            requesting_user_id=user_id,
            new_status=DecisionStatus.CLARIFYING,
        )
    )

    assert updated.status == DecisionStatus.CLARIFYING


@pytest.mark.asyncio
async def test_update_status_rejects_invalid_transition() -> None:
    decisions = InMemoryDecisionRepository()
    user_id = uuid4()
    decision = await CreateDecisionUseCase(decisions).execute(
        CreateDecisionInput(user_id=user_id, raw_input="X", vertical=DecisionVertical.CAREER)
    )

    with pytest.raises(InvalidStatusTransitionError):
        await UpdateDecisionStatusUseCase(decisions).execute(
            UpdateDecisionStatusInput(
                decision_id=decision.id,
                requesting_user_id=user_id,
                new_status=DecisionStatus.COMPLETED,
            )
        )


@pytest.mark.asyncio
async def test_update_status_raises_when_not_owner() -> None:
    decisions = InMemoryDecisionRepository()
    owner_id = uuid4()
    decision = await CreateDecisionUseCase(decisions).execute(
        CreateDecisionInput(user_id=owner_id, raw_input="X", vertical=DecisionVertical.CAREER)
    )

    with pytest.raises(DecisionNotFoundError):
        await UpdateDecisionStatusUseCase(decisions).execute(
            UpdateDecisionStatusInput(
                decision_id=decision.id,
                requesting_user_id=uuid4(),
                new_status=DecisionStatus.CLARIFYING,
            )
        )
