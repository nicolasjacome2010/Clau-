"""Domain entities for the billing bounded context (docs/DATABASE.md §2.12-2.13).

Stripe is the source of truth for subscription state (docs/ARCHITECTURE.md
§2.4/§9); `Subscription` here is a read replica synced exclusively by the
webhook handler (`HandleStripeWebhookEventUseCase`) — no other code path
is allowed to change `tier`/`status`/`current_period_end` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class SubscriptionTier(StrEnum):
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"
    TEAM = "team"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"


@dataclass(frozen=True, slots=True)
class Subscription:
    user_id: UUID
    stripe_customer_id: str
    stripe_subscription_id: str | None
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_end: datetime | None
    updated_at: datetime

    def with_webhook_state(
        self,
        *,
        stripe_subscription_id: str | None = None,
        tier: SubscriptionTier | None = None,
        status: SubscriptionStatus | None = None,
        current_period_end: datetime | None = None,
        at: datetime,
    ) -> Subscription:
        """Applies a partial update from one webhook event.

        A `None` argument means "this event type doesn't carry this field"
        (e.g. `invoice.payment_failed` only carries `status`), not "clear
        it" — the existing value is kept, never blanked out.
        """
        return replace(
            self,
            stripe_subscription_id=(
                stripe_subscription_id
                if stripe_subscription_id is not None
                else self.stripe_subscription_id
            ),
            tier=tier if tier is not None else self.tier,
            status=status if status is not None else self.status,
            current_period_end=(
                current_period_end if current_period_end is not None else self.current_period_end
            ),
            updated_at=at,
        )


@dataclass(frozen=True, slots=True)
class StripeEvent:
    """Append-only idempotency record (docs/DATABASE.md §2.13) — once a
    `stripe_event_id` is in this table, the webhook handler must treat a
    redelivery of that same event as a no-op, never reapply its effect.
    """

    stripe_event_id: str
    type: str
    payload: dict[str, Any]
    processed_at: datetime
