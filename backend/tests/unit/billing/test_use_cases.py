from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core_api.billing.application.use_cases import (
    CreateCheckoutSessionInput,
    CreateCheckoutSessionUseCase,
    CreatePortalSessionInput,
    CreatePortalSessionUseCase,
    GetSubscriptionUseCase,
    HandleStripeWebhookEventUseCase,
)
from core_api.billing.domain.entities import Subscription, SubscriptionStatus, SubscriptionTier
from core_api.billing.domain.exceptions import NoStripeCustomerError
from core_api.billing.domain.stripe_port import (
    CheckoutSessionResult,
    PortalSessionResult,
    StripeWebhookEvent,
)
from tests.unit.billing.fakes import (
    FakeStripeClient,
    InMemoryStripeEventRepository,
    InMemorySubscriptionRepository,
)


def _webhook_event(
    *,
    stripe_event_id: str = "evt_1",
    type: str = "checkout.session.completed",
    stripe_customer_id: str = "cus_1",
    user_id: object | None = None,
    stripe_subscription_id: str | None = "sub_1",
    tier: str | None = None,
    status: str | None = None,
    current_period_end: datetime | None = None,
) -> StripeWebhookEvent:
    return StripeWebhookEvent(
        stripe_event_id=stripe_event_id,
        type=type,
        stripe_customer_id=stripe_customer_id,
        user_id=user_id,  # type: ignore[arg-type]
        stripe_subscription_id=stripe_subscription_id,
        tier=tier,
        status=status,
        current_period_end=current_period_end,
        raw_payload={"id": stripe_event_id, "type": type},
    )


@pytest.mark.asyncio
async def test_get_subscription_returns_none_when_never_subscribed() -> None:
    subscriptions = InMemorySubscriptionRepository()

    result = await GetSubscriptionUseCase(subscriptions).execute(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_create_checkout_session_passes_existing_customer_id() -> None:
    subscriptions = InMemorySubscriptionRepository()
    stripe = FakeStripeClient(checkout_responses=[CheckoutSessionResult(checkout_url="https://x")])
    user_id = uuid4()
    now = datetime.now(UTC)
    await subscriptions.upsert(
        Subscription(
            user_id=user_id,
            stripe_customer_id="cus_existing",
            stripe_subscription_id=None,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )

    result = await CreateCheckoutSessionUseCase(subscriptions, stripe).execute(
        CreateCheckoutSessionInput(
            user_id=user_id,
            user_email="alejandro@example.com",
            price_id="price_pro",
            success_url="https://app/success",
            cancel_url="https://app/cancel",
        )
    )

    assert result.checkout_url == "https://x"
    assert stripe.checkout_calls == [(user_id, "price_pro", "cus_existing")]


@pytest.mark.asyncio
async def test_create_checkout_session_passes_none_customer_id_for_new_user() -> None:
    subscriptions = InMemorySubscriptionRepository()
    stripe = FakeStripeClient(checkout_responses=[CheckoutSessionResult(checkout_url="https://x")])
    user_id = uuid4()

    await CreateCheckoutSessionUseCase(subscriptions, stripe).execute(
        CreateCheckoutSessionInput(
            user_id=user_id,
            user_email="alejandro@example.com",
            price_id="price_pro",
            success_url="https://app/success",
            cancel_url="https://app/cancel",
        )
    )

    assert stripe.checkout_calls == [(user_id, "price_pro", None)]


@pytest.mark.asyncio
async def test_create_portal_session_raises_when_never_subscribed() -> None:
    subscriptions = InMemorySubscriptionRepository()
    stripe = FakeStripeClient()

    with pytest.raises(NoStripeCustomerError):
        await CreatePortalSessionUseCase(subscriptions, stripe).execute(
            CreatePortalSessionInput(user_id=uuid4(), return_url="https://app/account")
        )


@pytest.mark.asyncio
async def test_create_portal_session_returns_url_for_existing_customer() -> None:
    subscriptions = InMemorySubscriptionRepository()
    stripe = FakeStripeClient(portal_responses=[PortalSessionResult(portal_url="https://portal")])
    user_id = uuid4()
    now = datetime.now(UTC)
    await subscriptions.upsert(
        Subscription(
            user_id=user_id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )

    result = await CreatePortalSessionUseCase(subscriptions, stripe).execute(
        CreatePortalSessionInput(user_id=user_id, return_url="https://app/account")
    )

    assert result.portal_url == "https://portal"
    assert stripe.portal_calls == ["cus_1"]


@pytest.mark.asyncio
async def test_webhook_checkout_completed_creates_subscription_row() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()
    user_id = uuid4()

    await HandleStripeWebhookEventUseCase(subscriptions, events).execute(
        _webhook_event(
            type="checkout.session.completed",
            stripe_customer_id="cus_1",
            user_id=user_id,
            stripe_subscription_id="sub_1",
        )
    )

    stored = await subscriptions.get_by_user_id(user_id)
    assert stored is not None
    assert stored.stripe_customer_id == "cus_1"
    assert stored.stripe_subscription_id == "sub_1"
    assert stored.tier == SubscriptionTier.FREE  # not yet known until subscription.updated


@pytest.mark.asyncio
async def test_webhook_checkout_completed_without_client_reference_id_is_skipped() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()

    await HandleStripeWebhookEventUseCase(subscriptions, events).execute(
        _webhook_event(type="checkout.session.completed", user_id=None)
    )

    assert await subscriptions.get_by_stripe_customer_id("cus_1") is None
    assert await events.exists("evt_1")


@pytest.mark.asyncio
async def test_webhook_subscription_updated_applies_tier_and_status() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()
    user_id = uuid4()
    now = datetime.now(UTC)
    await subscriptions.upsert(
        Subscription(
            user_id=user_id,
            stripe_customer_id="cus_1",
            stripe_subscription_id=None,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )
    period_end = datetime(2026, 9, 1, tzinfo=UTC)

    await HandleStripeWebhookEventUseCase(subscriptions, events).execute(
        _webhook_event(
            stripe_event_id="evt_2",
            type="customer.subscription.updated",
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier="pro",
            status="active",
            current_period_end=period_end,
        )
    )

    updated = await subscriptions.get_by_user_id(user_id)
    assert updated is not None
    assert updated.tier == SubscriptionTier.PRO
    assert updated.status == SubscriptionStatus.ACTIVE
    assert updated.stripe_subscription_id == "sub_1"
    assert updated.current_period_end == period_end


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_marks_canceled() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()
    user_id = uuid4()
    now = datetime.now(UTC)
    await subscriptions.upsert(
        Subscription(
            user_id=user_id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )

    await HandleStripeWebhookEventUseCase(subscriptions, events).execute(
        _webhook_event(
            stripe_event_id="evt_3",
            type="customer.subscription.deleted",
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            status="canceled",
        )
    )

    updated = await subscriptions.get_by_user_id(user_id)
    assert updated is not None
    assert updated.status == SubscriptionStatus.CANCELED
    assert updated.tier == SubscriptionTier.PRO  # unaffected — event carried no tier


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed_marks_past_due() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()
    user_id = uuid4()
    now = datetime.now(UTC)
    await subscriptions.upsert(
        Subscription(
            user_id=user_id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )

    await HandleStripeWebhookEventUseCase(subscriptions, events).execute(
        _webhook_event(
            stripe_event_id="evt_4",
            type="invoice.payment_failed",
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            status="past_due",
        )
    )

    updated = await subscriptions.get_by_user_id(user_id)
    assert updated is not None
    assert updated.status == SubscriptionStatus.PAST_DUE


@pytest.mark.asyncio
async def test_webhook_subscription_event_for_unknown_customer_is_skipped() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()

    await HandleStripeWebhookEventUseCase(subscriptions, events).execute(
        _webhook_event(
            stripe_event_id="evt_5",
            type="customer.subscription.updated",
            stripe_customer_id="cus_unknown",
            status="active",
            tier="pro",
        )
    )

    assert await subscriptions.get_by_stripe_customer_id("cus_unknown") is None
    assert await events.exists("evt_5")


@pytest.mark.asyncio
async def test_webhook_event_is_idempotent() -> None:
    subscriptions = InMemorySubscriptionRepository()
    events = InMemoryStripeEventRepository()
    user_id = uuid4()
    now = datetime.now(UTC)
    await subscriptions.upsert(
        Subscription(
            user_id=user_id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )
    use_case = HandleStripeWebhookEventUseCase(subscriptions, events)
    event = _webhook_event(
        stripe_event_id="evt_6",
        type="customer.subscription.updated",
        stripe_customer_id="cus_1",
        stripe_subscription_id="sub_1",
        tier="pro",
        status="active",
    )

    await use_case.execute(event)
    first_update = await subscriptions.get_by_user_id(user_id)
    assert first_update is not None
    assert first_update.tier == SubscriptionTier.PRO

    # A redelivery of the exact same event must be a no-op, even if its
    # (hypothetical, malformed) payload would say something different.
    await use_case.execute(
        _webhook_event(
            stripe_event_id="evt_6",
            type="customer.subscription.updated",
            stripe_customer_id="cus_1",
            tier="elite",
            status="active",
        )
    )
    second_check = await subscriptions.get_by_user_id(user_id)
    assert second_check is not None
    assert second_check.tier == SubscriptionTier.PRO
