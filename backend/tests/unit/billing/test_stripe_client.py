"""Tests the Stripe adapter's own request/response handling against a
mocked `stripe.StripeClient` — no network call, no API key needed (there
is no `STRIPE_SECRET_KEY` in CI or this environment). What we verify is
*our* code: param wiring, signature-verification error mapping, and
webhook payload -> `StripeWebhookEvent` translation.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import stripe

from core_api.billing.domain.stripe_port import StripeError, StripeWebhookSignatureError
from core_api.billing.infrastructure.stripe_client import StripeApiClient


def _mock_stripe_client() -> MagicMock:
    client = MagicMock()
    client.checkout.sessions.create_async = AsyncMock()
    client.billing_portal.sessions.create_async = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_create_checkout_session_uses_existing_customer_id() -> None:
    client = _mock_stripe_client()
    client.checkout.sessions.create_async.return_value = SimpleNamespace(
        url="https://checkout.stripe.com/x"
    )
    adapter = StripeApiClient("sk_test", "whsec_test", client=client)
    user_id = uuid4()

    result = await adapter.create_checkout_session(
        user_id=user_id,
        user_email="alejandro@example.com",
        price_id="price_pro",
        stripe_customer_id="cus_1",
        success_url="https://app/success",
        cancel_url="https://app/cancel",
    )

    assert result.checkout_url == "https://checkout.stripe.com/x"
    params = client.checkout.sessions.create_async.call_args.args[0]
    assert params["customer"] == "cus_1"
    assert "customer_email" not in params
    assert params["client_reference_id"] == str(user_id)
    assert params["line_items"] == [{"price": "price_pro", "quantity": 1}]


@pytest.mark.asyncio
async def test_create_checkout_session_uses_email_for_new_customer() -> None:
    client = _mock_stripe_client()
    client.checkout.sessions.create_async.return_value = SimpleNamespace(
        url="https://checkout.stripe.com/x"
    )
    adapter = StripeApiClient("sk_test", "whsec_test", client=client)

    await adapter.create_checkout_session(
        user_id=uuid4(),
        user_email="alejandro@example.com",
        price_id="price_pro",
        stripe_customer_id=None,
        success_url="https://app/success",
        cancel_url="https://app/cancel",
    )

    params = client.checkout.sessions.create_async.call_args.args[0]
    assert params["customer_email"] == "alejandro@example.com"
    assert "customer" not in params


@pytest.mark.asyncio
async def test_create_checkout_session_raises_stripe_error_on_sdk_failure() -> None:
    client = _mock_stripe_client()
    client.checkout.sessions.create_async.side_effect = stripe.InvalidRequestError(
        "bad price", param="price"
    )
    adapter = StripeApiClient("sk_test", "whsec_test", client=client)

    with pytest.raises(StripeError):
        await adapter.create_checkout_session(
            user_id=uuid4(),
            user_email="alejandro@example.com",
            price_id="price_bad",
            stripe_customer_id=None,
            success_url="https://app/success",
            cancel_url="https://app/cancel",
        )


@pytest.mark.asyncio
async def test_create_portal_session_returns_url() -> None:
    client = _mock_stripe_client()
    client.billing_portal.sessions.create_async.return_value = SimpleNamespace(
        url="https://billing.stripe.com/x"
    )
    adapter = StripeApiClient("sk_test", "whsec_test", client=client)

    result = await adapter.create_portal_session(
        stripe_customer_id="cus_1", return_url="https://app/account"
    )

    assert result.portal_url == "https://billing.stripe.com/x"
    params = client.billing_portal.sessions.create_async.call_args.args[0]
    assert params == {"customer": "cus_1", "return_url": "https://app/account"}


def test_construct_webhook_event_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = StripeApiClient("sk_test", "whsec_test", client=_mock_stripe_client())

    def _raise(*args: object, **kwargs: object) -> None:
        raise stripe.SignatureVerificationError("bad signature", "sig_header")

    monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)

    with pytest.raises(StripeWebhookSignatureError):
        adapter.construct_webhook_event(b"{}", "t=1,v1=bad")


def test_construct_webhook_event_translates_checkout_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = StripeApiClient("sk_test", "whsec_test", client=_mock_stripe_client())
    user_id = uuid4()
    event = stripe.Event.construct_from(
        {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "client_reference_id": str(user_id),
                }
            },
        },
        "sk_test",
    )
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **k: event)

    result = adapter.construct_webhook_event(b"{}", "t=1,v1=fake")

    assert result.stripe_event_id == "evt_1"
    assert result.type == "checkout.session.completed"
    assert result.stripe_customer_id == "cus_1"
    assert result.user_id == user_id
    assert result.stripe_subscription_id == "sub_1"
    assert result.tier is None


def test_construct_webhook_event_translates_subscription_updated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = StripeApiClient("sk_test", "whsec_test", client=_mock_stripe_client())
    event = stripe.Event.construct_from(
        {
            "id": "evt_2",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_1",
                    "customer": "cus_1",
                    "status": "active",
                    "current_period_end": 1893456000,
                    "items": {"data": [{"price": {"id": "price_1", "metadata": {"tier": "pro"}}}]},
                }
            },
        },
        "sk_test",
    )
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **k: event)

    result = adapter.construct_webhook_event(b"{}", "t=1,v1=fake")

    assert result.stripe_subscription_id == "sub_1"
    assert result.status == "active"
    assert result.tier == "pro"
    assert result.current_period_end is not None
    assert result.user_id is None


def test_construct_webhook_event_translates_invoice_payment_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = StripeApiClient("sk_test", "whsec_test", client=_mock_stripe_client())
    event = stripe.Event.construct_from(
        {
            "id": "evt_3",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_1", "subscription": "sub_1"}},
        },
        "sk_test",
    )
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **k: event)

    result = adapter.construct_webhook_event(b"{}", "t=1,v1=fake")

    assert result.status == "past_due"
    assert result.stripe_subscription_id == "sub_1"
