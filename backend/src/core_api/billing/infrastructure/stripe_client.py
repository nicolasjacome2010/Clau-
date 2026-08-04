"""Stripe implementation of the billing port.

Uses Stripe's modern resource-based client (`stripe.StripeClient`), whose
`*_async` methods are genuinely async (backed by `httpx`), so
`create_checkout_session`/`create_portal_session` never block the event
loop the way calling the legacy module-level Stripe API would.
`construct_webhook_event` stays synchronous: signature verification is
pure CPU/crypto work over bytes already read off the request, not a call
to Stripe.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import stripe

from core_api.billing.domain.stripe_port import (
    CheckoutSessionResult,
    PortalSessionResult,
    StripeClient,
    StripeError,
    StripeWebhookEvent,
    StripeWebhookSignatureError,
)

_SUBSCRIPTION_EVENT_TYPES = {"customer.subscription.updated", "customer.subscription.deleted"}


class StripeApiClient(StripeClient):
    def __init__(
        self, api_key: str, webhook_secret: str, *, client: stripe.StripeClient | None = None
    ) -> None:
        self._client = client or stripe.StripeClient(api_key)
        self._webhook_secret = webhook_secret

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
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(user_id),
        }
        if stripe_customer_id:
            params["customer"] = stripe_customer_id
        else:
            params["customer_email"] = user_email

        try:
            # `create_async` expects Stripe's generated `CreateParams`
            # TypedDict; a plain dict matches its structure at runtime but
            # mypy can't verify that without importing every nested
            # TypedDict variant, so this one boundary is deliberately Any.
            session = await self._client.checkout.sessions.create_async(cast(Any, params))
        except stripe.StripeError as exc:
            raise StripeError(f"Stripe checkout session creation failed: {exc}") from exc

        if not session.url:
            raise StripeError("Stripe did not return a checkout URL")
        return CheckoutSessionResult(checkout_url=session.url)

    async def create_portal_session(
        self, *, stripe_customer_id: str, return_url: str
    ) -> PortalSessionResult:
        try:
            session = await self._client.billing_portal.sessions.create_async(
                {"customer": stripe_customer_id, "return_url": return_url}
            )
        except stripe.StripeError as exc:
            raise StripeError(f"Stripe portal session creation failed: {exc}") from exc
        return PortalSessionResult(portal_url=session.url)

    def construct_webhook_event(self, payload: bytes, signature_header: str) -> StripeWebhookEvent:
        try:
            # `stripe`'s own stub for `construct_event` is untyped (a
            # third-party gap, not ours) — the `cast` below documents the
            # real contract instead of leaving an unchecked `Any`.
            event = cast(
                "stripe.Event",
                stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
                    payload, signature_header, self._webhook_secret
                ),
            )
        except stripe.SignatureVerificationError as exc:
            raise StripeWebhookSignatureError(f"Invalid Stripe webhook signature: {exc}") from exc
        except ValueError as exc:
            raise StripeWebhookSignatureError(f"Malformed Stripe webhook payload: {exc}") from exc

        obj = event.data.object
        stripe_customer_id = cast(str, obj["customer"])

        user_id: UUID | None = None
        stripe_subscription_id: str | None = None
        tier: str | None = None
        status: str | None = None
        current_period_end: datetime | None = None

        if event.type == "checkout.session.completed":
            client_reference_id = obj.get("client_reference_id")
            user_id = UUID(client_reference_id) if client_reference_id else None
            stripe_subscription_id = obj.get("subscription")
        elif event.type in _SUBSCRIPTION_EVENT_TYPES:
            stripe_subscription_id = obj.get("id")
            status = obj.get("status")
            period_end = obj.get("current_period_end")
            if period_end is not None:
                current_period_end = datetime.fromtimestamp(period_end, tz=UTC)
            items = obj.get("items", {}).get("data", [])
            if items:
                tier = items[0].get("price", {}).get("metadata", {}).get("tier")
        elif event.type == "invoice.payment_failed":
            stripe_subscription_id = obj.get("subscription")
            status = "past_due"

        return StripeWebhookEvent(
            stripe_event_id=event.id,
            type=event.type,
            stripe_customer_id=stripe_customer_id,
            user_id=user_id,
            stripe_subscription_id=stripe_subscription_id,
            tier=tier,
            status=status,
            current_period_end=current_period_end,
            raw_payload=dict(event),
        )
