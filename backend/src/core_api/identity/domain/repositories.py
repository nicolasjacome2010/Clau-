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

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Erases the user and, by the schema's own cascade, everything
        that hangs off them (docs/DATABASE.md: every user-owned table is
        `ON DELETE CASCADE` from `users.id`).

        Deliberately *not* six hand-written deletes across six contexts:
        the ownership tree is already declared in the schema, and a
        second copy of it in application code is a copy that drifts the
        day someone adds a table. Returns False when there was no such
        user, so a caller can tell "erased" from "nothing to erase".
        """


class UserProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None: ...

    @abstractmethod
    async def upsert(self, profile: UserProfile) -> UserProfile: ...
