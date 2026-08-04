"""Domain-level errors for the billing bounded context."""

from __future__ import annotations

from uuid import UUID


class BillingDomainError(Exception):
    """Base class for all billing domain errors."""


class NoStripeCustomerError(BillingDomainError):
    """Raised when opening the Stripe Customer Portal for a user with no
    `Subscription` row yet — a user must complete Checkout at least once
    (which creates the Stripe customer) before a portal session makes
    sense.
    """

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} has no Stripe customer to manage")
