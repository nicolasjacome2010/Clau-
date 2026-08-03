"""Application use cases for the identity bounded context.

Each use case is a single, orchestrated unit of business logic. They depend
only on domain repository interfaces, never on infrastructure directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core_api.identity.domain.entities import User, UserProfile
from core_api.identity.domain.exceptions import UserNotFoundError
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """What we trust from a verified JWT (see core_api/auth)."""

    id: UUID
    email: str


class GetOrCreateUserUseCase:
    """Just-in-time provisioning: the first authenticated request from a
    Supabase-issued JWT materializes the domain User in our own database
    (see docs/ARCHITECTURE.md §8 — Supabase is the credential source of
    truth, Core API owns the domain replica).
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def execute(self, identity: AuthenticatedIdentity) -> User:
        existing = await self._users.get_by_id(identity.id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        new_user = User(
            id=identity.id,
            email=identity.email,
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
        return await self._users.create(new_user)


@dataclass(frozen=True, slots=True)
class UpdateUserProfileInput:
    user_id: UUID
    life_context: dict[str, Any] | None = None
    risk_tolerance: int | None = None
    timezone: str | None = None


class UpdateUserProfileUseCase:
    """Creates the profile on first write, updates it thereafter (upsert)."""

    def __init__(
        self,
        user_repository: UserRepository,
        profile_repository: UserProfileRepository,
    ) -> None:
        self._users = user_repository
        self._profiles = profile_repository

    async def execute(self, data: UpdateUserProfileInput) -> UserProfile:
        user = await self._users.get_by_id(data.user_id)
        if user is None:
            raise UserNotFoundError(data.user_id)

        current = await self._profiles.get_by_user_id(data.user_id)
        updated = UserProfile(
            user_id=data.user_id,
            life_context=(
                data.life_context
                if data.life_context is not None
                else (current.life_context if current else {})
            ),
            risk_tolerance=(
                data.risk_tolerance
                if data.risk_tolerance is not None
                else (current.risk_tolerance if current else 3)
            ),
            timezone=(
                data.timezone
                if data.timezone is not None
                else (current.timezone if current else "UTC")
            ),
        )
        return await self._profiles.upsert(updated)
