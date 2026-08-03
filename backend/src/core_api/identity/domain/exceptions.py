"""Domain-level errors for the identity bounded context."""

from __future__ import annotations

from uuid import UUID


class IdentityDomainError(Exception):
    """Base class for all identity domain errors."""


class UserNotFoundError(IdentityDomainError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} was not found")
