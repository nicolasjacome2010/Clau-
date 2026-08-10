from __future__ import annotations

from uuid import uuid4

import pytest

from core_api.goals.application.use_cases import (
    CreateGoalInput,
    CreateGoalUseCase,
    ListActiveGoalsUseCase,
    UpdateGoalInput,
    UpdateGoalUseCase,
)
from core_api.goals.domain.exceptions import GoalNotFoundError
from tests.unit.goals.fakes import InMemoryGoalRepository


@pytest.mark.asyncio
async def test_create_goal_defaults_to_active_and_weight_50() -> None:
    goals = InMemoryGoalRepository()
    user_id = uuid4()

    goal = await CreateGoalUseCase(goals).execute(
        CreateGoalInput(user_id=user_id, name="  Estabilidad financiera  ")
    )

    assert goal.name == "Estabilidad financiera"  # trimmed
    assert goal.default_weight == 50
    assert goal.is_active is True


@pytest.mark.asyncio
async def test_list_active_goals_excludes_inactive_and_other_users() -> None:
    goals = InMemoryGoalRepository()
    user_id = uuid4()
    other_user_id = uuid4()
    use_case = CreateGoalUseCase(goals)
    mine = await use_case.execute(CreateGoalInput(user_id=user_id, name="Crecimiento"))
    await use_case.execute(CreateGoalInput(user_id=other_user_id, name="No es mío"))
    inactive = await use_case.execute(CreateGoalInput(user_id=user_id, name="Ya no aplica"))
    await UpdateGoalUseCase(goals).execute(
        UpdateGoalInput(goal_id=inactive.id, requesting_user_id=user_id, is_active=False)
    )

    active = await ListActiveGoalsUseCase(goals).execute(user_id)

    assert [g.id for g in active] == [mine.id]


@pytest.mark.asyncio
async def test_update_goal_changes_only_provided_fields() -> None:
    goals = InMemoryGoalRepository()
    user_id = uuid4()
    goal = await CreateGoalUseCase(goals).execute(CreateGoalInput(user_id=user_id, name="Libertad"))

    updated = await UpdateGoalUseCase(goals).execute(
        UpdateGoalInput(goal_id=goal.id, requesting_user_id=user_id, default_weight=80)
    )

    assert updated.name == "Libertad"
    assert updated.default_weight == 80
    assert updated.is_active is True


@pytest.mark.asyncio
async def test_update_goal_raises_when_owned_by_another_user() -> None:
    goals = InMemoryGoalRepository()
    owner_id = uuid4()
    attacker_id = uuid4()
    goal = await CreateGoalUseCase(goals).execute(CreateGoalInput(user_id=owner_id, name="Privado"))

    with pytest.raises(GoalNotFoundError):
        await UpdateGoalUseCase(goals).execute(
            UpdateGoalInput(goal_id=goal.id, requesting_user_id=attacker_id, name="hijack")
        )


@pytest.mark.asyncio
async def test_update_goal_raises_when_goal_does_not_exist() -> None:
    goals = InMemoryGoalRepository()

    with pytest.raises(GoalNotFoundError):
        await UpdateGoalUseCase(goals).execute(
            UpdateGoalInput(goal_id=uuid4(), requesting_user_id=uuid4(), name="ghost")
        )
