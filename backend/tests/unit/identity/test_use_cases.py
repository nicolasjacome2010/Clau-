from __future__ import annotations

from uuid import uuid4

import pytest

from core_api.identity.application.use_cases import (
    AuthenticatedIdentity,
    GetOrCreateUserUseCase,
    UpdateUserProfileInput,
    UpdateUserProfileUseCase,
)
from core_api.identity.domain.exceptions import UserNotFoundError
from tests.unit.identity.fakes import InMemoryUserProfileRepository, InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_or_create_user_creates_on_first_call() -> None:
    users = InMemoryUserRepository()
    identity = AuthenticatedIdentity(id=uuid4(), email="alejandro@example.com")

    user = await GetOrCreateUserUseCase(users).execute(identity)

    assert user.id == identity.id
    assert user.email == identity.email
    assert user.onboarding_completed_at is None


@pytest.mark.asyncio
async def test_get_or_create_user_is_idempotent() -> None:
    users = InMemoryUserRepository()
    identity = AuthenticatedIdentity(id=uuid4(), email="marina@example.com")
    use_case = GetOrCreateUserUseCase(users)

    first = await use_case.execute(identity)
    second = await use_case.execute(identity)

    assert first == second
    assert len(users._users) == 1  # no duplicate row was created


@pytest.mark.asyncio
async def test_update_profile_creates_profile_with_defaults_when_absent() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryUserProfileRepository()
    identity = AuthenticatedIdentity(id=uuid4(), email="javier@example.com")
    await GetOrCreateUserUseCase(users).execute(identity)

    updated = await UpdateUserProfileUseCase(users, profiles).execute(
        UpdateUserProfileInput(user_id=identity.id, risk_tolerance=2)
    )

    assert updated.risk_tolerance == 2
    assert updated.timezone == "UTC"  # default preserved
    assert updated.life_context == {}


@pytest.mark.asyncio
async def test_update_profile_preserves_untouched_fields_on_partial_update() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryUserProfileRepository()
    identity = AuthenticatedIdentity(id=uuid4(), email="alejandro@example.com")
    await GetOrCreateUserUseCase(users).execute(identity)
    use_case = UpdateUserProfileUseCase(users, profiles)

    await use_case.execute(
        UpdateUserProfileInput(user_id=identity.id, timezone="Europe/Lisbon", risk_tolerance=4)
    )
    updated = await use_case.execute(
        UpdateUserProfileInput(user_id=identity.id, life_context={"occupation": "PM"})
    )

    assert updated.timezone == "Europe/Lisbon"
    assert updated.risk_tolerance == 4
    assert updated.life_context == {"occupation": "PM"}


@pytest.mark.asyncio
async def test_update_profile_raises_when_user_does_not_exist() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryUserProfileRepository()

    with pytest.raises(UserNotFoundError):
        await UpdateUserProfileUseCase(users, profiles).execute(
            UpdateUserProfileInput(user_id=uuid4(), risk_tolerance=1)
        )
