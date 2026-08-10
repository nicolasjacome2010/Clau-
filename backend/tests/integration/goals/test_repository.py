from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.goals.domain.entities import Goal
from core_api.goals.infrastructure.repository import SqlAlchemyGoalRepository
from core_api.identity.domain.entities import User
from core_api.identity.infrastructure.repository import SqlAlchemyUserRepository


async def _create_user(session: AsyncSession) -> User:
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        display_name=None,
        locale="es",
        onboarding_completed_at=None,
        created_at=now,
        updated_at=now,
    )
    return await SqlAlchemyUserRepository(session).create(user)


@pytest.mark.asyncio
async def test_create_and_get_goal_round_trips(sqlite_session: AsyncSession) -> None:
    user = await _create_user(sqlite_session)
    repo = SqlAlchemyGoalRepository(sqlite_session)
    goal = Goal(
        id=uuid4(),
        user_id=user.id,
        name="Crecimiento profesional",
        default_weight=70,
        is_active=True,
        created_at=datetime.now(UTC),
    )

    created = await repo.create(goal)
    fetched = await repo.get_by_id(goal.id)

    assert created == goal
    assert fetched == goal


@pytest.mark.asyncio
async def test_list_for_user_filters_by_active_and_ownership(sqlite_session: AsyncSession) -> None:
    user = await _create_user(sqlite_session)
    other_user = await _create_user(sqlite_session)
    repo = SqlAlchemyGoalRepository(sqlite_session)
    now = datetime.now(UTC)
    mine_active = await repo.create(
        Goal(
            id=uuid4(),
            user_id=user.id,
            name="Mío activo",
            default_weight=50,
            is_active=True,
            created_at=now,
        )
    )
    await repo.create(
        Goal(
            id=uuid4(),
            user_id=user.id,
            name="Mío inactivo",
            default_weight=50,
            is_active=False,
            created_at=now,
        )
    )
    await repo.create(
        Goal(
            id=uuid4(),
            user_id=other_user.id,
            name="De otro",
            default_weight=50,
            is_active=True,
            created_at=now,
        )
    )

    result = await repo.list_for_user(user.id, active_only=True)

    assert [g.id for g in result] == [mine_active.id]


@pytest.mark.asyncio
async def test_update_goal_persists_changes(sqlite_session: AsyncSession) -> None:
    user = await _create_user(sqlite_session)
    repo = SqlAlchemyGoalRepository(sqlite_session)
    goal = await repo.create(
        Goal(
            id=uuid4(),
            user_id=user.id,
            name="Original",
            default_weight=50,
            is_active=True,
            created_at=datetime.now(UTC),
        )
    )

    updated = await repo.update(
        Goal(
            id=goal.id,
            user_id=user.id,
            name="Renombrado",
            default_weight=90,
            is_active=False,
            created_at=goal.created_at,
        )
    )
    fetched = await repo.get_by_id(goal.id)

    assert updated.name == "Renombrado"
    assert fetched is not None
    assert fetched.is_active is False
    assert fetched.default_weight == 90
