"""In-memory fakes of the identity repositories, used only by unit tests.

These implement the same abstract interfaces the real SQLAlchemy
repositories do, so use cases are tested against the domain contract, not
against a specific persistence technology.
"""

from __future__ import annotations

from uuid import UUID

from core_api.identity.domain.entities import User, UserProfile
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def create(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def update(self, user: User) -> User:
        if user.id not in self._users:
            raise ValueError(f"Cannot update non-existent user {user.id}")
        self._users[user.id] = user
        return user


class InMemoryUserProfileRepository(UserProfileRepository):
    def __init__(self) -> None:
        self._profiles: dict[UUID, UserProfile] = {}

    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        return self._profiles.get(user_id)

    async def upsert(self, profile: UserProfile) -> UserProfile:
        self._profiles[profile.user_id] = profile
        return profile
