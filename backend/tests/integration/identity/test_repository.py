from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.identity.domain.entities import User, UserProfile
from core_api.identity.infrastructure.repository import (
    SqlAlchemyUserProfileRepository,
    SqlAlchemyUserRepository,
)


@pytest.mark.asyncio
async def test_create_and_get_user_round_trips(sqlite_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(sqlite_session)
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email="alejandro@example.com",
        display_name="Alejandro",
        locale="es",
        onboarding_completed_at=None,
        created_at=now,
        updated_at=now,
    )

    created = await repo.create(user)
    fetched = await repo.get_by_id(user.id)

    assert created == user
    assert fetched == user


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(sqlite_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(sqlite_session)

    assert await repo.get_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_profile_upsert_inserts_then_updates(sqlite_session: AsyncSession) -> None:
    user_repo = SqlAlchemyUserRepository(sqlite_session)
    profile_repo = SqlAlchemyUserProfileRepository(sqlite_session)
    now = datetime.now(UTC)
    user_id = uuid4()
    await user_repo.create(
        User(
            id=user_id,
            email="marina@example.com",
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
    )

    await profile_repo.upsert(UserProfile(user_id=user_id, risk_tolerance=2, timezone="UTC"))
    updated = await profile_repo.upsert(
        UserProfile(user_id=user_id, risk_tolerance=5, timezone="Europe/Lisbon")
    )
    fetched = await profile_repo.get_by_user_id(user_id)

    assert updated.risk_tolerance == 5
    assert fetched is not None
    assert fetched.timezone == "Europe/Lisbon"
