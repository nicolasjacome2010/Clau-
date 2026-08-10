"""Application use cases for the billing bounded context.

`HandleStripeWebhookEventUseCase` is the only place that writes to
`Subscription` — everywhere else in this module (and in every other
bounded context) only reads it, matching Stripe-is-the-source-of-truth
(docs/ARCHITECTURE.md §2.4/§9).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from core_api.billing.domain.entities import (
    StripeEvent,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)
from core_api.billing.domain.exceptions import NoStripeCustomerError
from core_api.billing.domain.repositories import StripeEventRepository, SubscriptionRepository
from core_api.billing.domain.stripe_port import (
    CheckoutSessionResult,
    PortalSessionResult,
    StripeClient,
    StripeWebhookEvent,
)

_SUBSCRIPTION_STATE_EVENT_TYPES = {
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
}


class GetSubscriptionUseCase:
    def __init__(self, subscription_repository: SubscriptionRepository) -> None:
        self._subscriptions = subscription_repository

    async def execute(self, user_id: UUID) -> Subscription | None:
        # `None` means "free tier, never subscribed" — there is
        # deliberately no `Subscription` row for that case (see
        # docs/DATABASE.md §2.12); the API layer maps `None` to the
        # free-tier default response.
        return await self._subscriptions.get_by_user_id(user_id)


@dataclass(frozen=True, slots=True)
class CreateCheckoutSessionInput:
    user_id: UUID
    user_email: str
    price_id: str
    success_url: str
    cancel_url: str


class CreateCheckoutSessionUseCase:
    def __init__(
        self, subscription_repository: SubscriptionRepository, stripe_client: StripeClient
    ) -> None:
        self._subscriptions = subscription_repository
        self._stripe = stripe_client

    async def execute(self, data: CreateCheckoutSessionInput) -> CheckoutSessionResult:
        existing = await self._subscriptions.get_by_user_id(data.user_id)
        return await self._stripe.create_checkout_session(
            user_id=data.user_id,
            user_email=data.user_email,
            price_id=data.price_id,
            stripe_customer_id=existing.stripe_customer_id if existing else None,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )


@dataclass(frozen=True, slots=True)
class CreatePortalSessionInput:
    user_id: UUID
    return_url: str


class CreatePortalSessionUseCase:
    def __init__(
        self, subscription_repository: SubscriptionRepository, stripe_client: StripeClient
    ) -> None:
        self._subscriptions = subscription_repository
        self._stripe = stripe_client

    async def execute(self, data: CreatePortalSessionInput) -> PortalSessionResult:
        subscription = await self._subscriptions.get_by_user_id(data.user_id)
        if subscription is None:
            raise NoStripeCustomerError(data.user_id)
        return await self._stripe.create_portal_session(
            stripe_customer_id=subscription.stripe_customer_id, return_url=data.return_url
        )


class HandleStripeWebhookEventUseCase:
    """Idempotent webhook processing (docs/ARCHITECTURE.md §9): every event
    is recorded in `stripe_events` keyed by Stripe's own `stripe_event_id`,
    so a redelivered event (Stripe retries until it gets a 2xx) is a no-op
    rather than reapplied.
    """

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        stripe_event_repository: StripeEventRepository,
    ) -> None:
        self._subscriptions = subscription_repository
        self._events = stripe_event_repository

    async def execute(self, event: StripeWebhookEvent) -> None:
        if await self._events.exists(event.stripe_event_id):
            return

        now = datetime.now(UTC)

        if event.type == "checkout.session.completed":
            await self._apply_checkout_completed(event, now)
        elif event.type in _SUBSCRIPTION_STATE_EVENT_TYPES:
            await self._apply_subscription_state(event, now)
        # Any other event type Stripe sends is recorded as processed below
        # and otherwise has no effect — forward-compatible with Stripe's
        # own "ignore event types you don't handle" guidance.

        await self._events.create(
            StripeEvent(
                stripe_event_id=event.stripe_event_id,
                type=event.type,
                payload=event.raw_payload,
                processed_at=now,
            )
        )

    async def _apply_checkout_completed(self, event: StripeWebhookEvent, now: datetime) -> None:
        if event.user_id is None:
            return  # No `client_reference_id` — nothing to link to a user.

        existing = await self._subscriptions.get_by_stripe_customer_id(event.stripe_customer_id)
        base = existing or Subscription(
            user_id=event.user_id,
            stripe_customer_id=event.stripe_customer_id,
            stripe_subscription_id=None,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
        updated = base.with_webhook_state(
            stripe_subscription_id=event.stripe_subscription_id, at=now
        )
        await self._subscriptions.upsert(updated)

    async def _apply_subscription_state(self, event: StripeWebhookEvent, now: datetime) -> None:
        existing = await self._subscriptions.get_by_stripe_customer_id(event.stripe_customer_id)
        if existing is None:
            # A subscription-lifecycle event for a Stripe customer we've
            # never linked to a user (created outside our own Checkout
            # flow, e.g. from the Stripe dashboard) — there is no row to
            # update. Still recorded as processed above: retrying wouldn't
            # change that there's nothing to link it to.
            return

        tier = SubscriptionTier(event.tier) if event.tier is not None else None
        status = SubscriptionStatus(event.status) if event.status is not None else None
        updated = existing.with_webhook_state(
            stripe_subscription_id=event.stripe_subscription_id,
            tier=tier,
            status=status,
            current_period_end=event.current_period_end,
            at=now,
        )
        await self._subscriptions.upsert(updated)
