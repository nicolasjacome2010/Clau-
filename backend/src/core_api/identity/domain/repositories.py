"""Repository interfaces (ports) for the identity bounded context.

Concrete implementations live in `identity/infrastructure`. Application
use cases depend only on these abstractions (Dependency Inversion —
see docs/ARCHITECTURE.md §4).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core_api.identity.domain.entities import User, UserProfile


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...


class UserProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None: ...

    @abstractmethod
    async def upsert(self, profile: UserProfile) -> UserProfile: ...
