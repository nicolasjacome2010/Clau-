"""Domain-level errors for the privacy bounded context."""

from __future__ import annotations

from uuid import UUID


class PrivacyDomainError(Exception):
    """Base class for all privacy domain errors."""


class ActiveSubscriptionError(PrivacyDomainError):
    """Raised when erasure is requested while a paid plan is still live.

    Erasing the local rows would drop this service's copy of the
    subscription while Stripe keeps billing the card: the user would go on
    paying for an account that no longer exists here. Cancelling on the
    user's behalf isn't the answer either — that is a money decision, and
    the Customer Portal is where they make it (docs/ARCHITECTURE.md §9:
    Stripe is the source of truth, this service never mutates it).

    So the request is refused with the reason, not silently reinterpreted.
    """

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} still has an active paid subscription")


class UserNotFoundError(PrivacyDomainError):
    """Raised when there is no such user to export or erase."""

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} was not found")
