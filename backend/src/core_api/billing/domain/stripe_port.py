"""Port for calling Stripe (docs/ARCHITECTURE.md §2.4/§9).

Stripe's own SDK types never cross into `application/` or `domain/` —
`infrastructure/stripe_client.py` is the only file that imports `stripe`
and translates its wire shapes into these plain DTOs, same pattern as
`simulations/domain/reality_engine_port.py` for the Reality Engine
boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CheckoutSessionResult:
    checkout_url: str


@dataclass(frozen=True, slots=True)
class PortalSessionResult:
    portal_url: str


@dataclass(frozen=True, slots=True)
class StripeWebhookEvent:
    """What this module needs out of one verified Stripe webhook event.

    Fields a given event type doesn't carry are `None` — see
    `Subscription.with_webhook_state`'s partial-update semantics, which
    this shape is designed to feed directly.
    """

    stripe_event_id: str
    type: str
    stripe_customer_id: str
    user_id: UUID | None
    """Only `checkout.session.completed` carries this (via
    `client_reference_id`) — it's how a `stripe_customer_id` gets linked to
    a domain user for the first time.
    """
    stripe_subscription_id: str | None
    tier: str | None
    status: str | None
    current_period_end: datetime | None
    raw_payload: dict[str, Any]


class StripeError(Exception):
    """Raised for any failure calling Stripe: network error, API error."""


class StripeWebhookSignatureError(StripeError):
    """Raised when a webhook payload's signature doesn't verify against the
    configured webhook secret — the caller must respond 400 and must never
    process the payload.
    """


class StripeClient(ABC):
    @abstractmethod
    async def create_checkout_session(
        self,
        *,
        user_id: UUID,
        user_email: str,
        price_id: str,
        stripe_customer_id: str | None,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult: ...

    @abstractmethod
    async def create_portal_session(
        self, *, stripe_customer_id: str, return_url: str
    ) -> PortalSessionResult: ...

    @abstractmethod
    def construct_webhook_event(
        self, payload: bytes, signature_header: str
    ) -> StripeWebhookEvent:
        """Synchronous by design: verifying a webhook signature is pure
        CPU/crypto work over the already-received request body, not a
        network call to Stripe.
        """
        ...
