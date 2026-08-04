"""In-memory/fake doubles for the billing bounded context, used only by
unit tests.
"""

from __future__ import annotations

from uuid import UUID

from core_api.billing.domain.entities import StripeEvent, Subscription
from core_api.billing.domain.repositories import StripeEventRepository, SubscriptionRepository
from core_api.billing.domain.stripe_port import (
    CheckoutSessionResult,
    PortalSessionResult,
    StripeClient,
    StripeError,
    StripeWebhookEvent,
)


class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self) -> None:
        self._subscriptions: dict[UUID, Subscription] = {}

    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        return self._subscriptions.get(user_id)

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Subscription | None:
        return next(
            (s for s in self._subscriptions.values() if s.stripe_customer_id == stripe_customer_id),
            None,
        )

    async def upsert(self, subscription: Subscription) -> Subscription:
        self._subscriptions[subscription.user_id] = subscription
        return subscription


class InMemoryStripeEventRepository(StripeEventRepository):
    def __init__(self) -> None:
        self._events: dict[str, StripeEvent] = {}

    async def exists(self, stripe_event_id: str) -> bool:
        return stripe_event_id in self._events

    async def create(self, event: StripeEvent) -> StripeEvent:
        self._events[event.stripe_event_id] = event
        return event


class FakeStripeClient(StripeClient):
    """Returns canned results/errors from the given lists, in order — same
    pattern as `simulations`' `FakeRealityEngineClient`.
    """

    def __init__(
        self,
        checkout_responses: list[CheckoutSessionResult | StripeError] | None = None,
        portal_responses: list[PortalSessionResult | StripeError] | None = None,
        webhook_events: list[StripeWebhookEvent] | None = None,
    ) -> None:
        self._checkout_responses = list(checkout_responses or [])
        self._portal_responses = list(portal_responses or [])
        self._webhook_events = list(webhook_events or [])
        self.checkout_calls: list[tuple[UUID, str, str | None]] = []
        self.portal_calls: list[str] = []

    async def create_checkout_session(
        self,
        *,
        user_id: UUID,
        user_email: str,
        price_id: str,
        stripe_customer_id: str | None,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        self.checkout_calls.append((user_id, price_id, stripe_customer_id))
        if not self._checkout_responses:
            raise StripeError("FakeStripeClient has no more canned checkout responses")
        result = self._checkout_responses.pop(0)
        if isinstance(result, StripeError):
            raise result
        return result

    async def create_portal_session(
        self, *, stripe_customer_id: str, return_url: str
    ) -> PortalSessionResult:
        self.portal_calls.append(stripe_customer_id)
        if not self._portal_responses:
            raise StripeError("FakeStripeClient has no more canned portal responses")
        result = self._portal_responses.pop(0)
        if isinstance(result, StripeError):
            raise result
        return result

    def construct_webhook_event(self, payload: bytes, signature_header: str) -> StripeWebhookEvent:
        if not self._webhook_events:
            raise StripeError("FakeStripeClient has no more canned webhook events")
        return self._webhook_events.pop(0)

    def queue_webhook_event(self, event: StripeWebhookEvent) -> None:
        self._webhook_events.append(event)
