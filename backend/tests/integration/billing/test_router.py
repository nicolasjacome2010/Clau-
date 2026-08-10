from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.billing.domain.entities import Subscription, SubscriptionStatus, SubscriptionTier
from core_api.billing.domain.stripe_port import (
    CheckoutSessionResult,
    PortalSessionResult,
    StripeWebhookEvent,
)
from core_api.dependencies import (
    get_stripe_client,
    get_stripe_event_repository,
    get_subscription_repository,
    get_token_verifier,
)
from core_api.main import create_app
from tests.unit.billing.fakes import (
    FakeStripeClient,
    InMemoryStripeEventRepository,
    InMemorySubscriptionRepository,
)

AUTH = {"Authorization": "Bearer valid-token"}
USER_ID = uuid4()


@pytest.fixture
def stripe_client() -> FakeStripeClient:
    return FakeStripeClient(
        checkout_responses=[CheckoutSessionResult(checkout_url="https://checkout.stripe.com/x")],
        portal_responses=[PortalSessionResult(portal_url="https://billing.stripe.com/x")],
    )


@pytest.fixture
def subscriptions() -> InMemorySubscriptionRepository:
    return InMemorySubscriptionRepository()


@pytest.fixture
def client(
    stripe_client: FakeStripeClient, subscriptions: InMemorySubscriptionRepository
) -> Iterator[TestClient]:
    app = create_app()

    events = InMemoryStripeEventRepository()
    identity = VerifiedIdentity(id=USER_ID, email="alejandro@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity})

    app.dependency_overrides[get_subscription_repository] = lambda: subscriptions
    app.dependency_overrides[get_stripe_event_repository] = lambda: events
    app.dependency_overrides[get_stripe_client] = lambda: stripe_client
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


def test_get_subscription_defaults_to_free_when_never_subscribed(client: TestClient) -> None:
    response = client.get("/v1/billing/subscription", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "free"
    assert body["status"] == "active"
    assert body["current_period_end"] is None


@pytest.mark.asyncio
async def test_get_subscription_returns_stored_state(
    client: TestClient, subscriptions: InMemorySubscriptionRepository
) -> None:
    await subscriptions.upsert(
        Subscription(
            user_id=USER_ID,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=datetime.now(UTC),
        )
    )

    response = client.get("/v1/billing/subscription", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["tier"] == "pro"


def test_create_checkout_session_returns_url(client: TestClient) -> None:
    response = client.post(
        "/v1/billing/checkout-session",
        headers=AUTH,
        json={
            "price_id": "price_pro",
            "success_url": "https://app/success",
            "cancel_url": "https://app/cancel",
        },
    )

    assert response.status_code == 201
    assert response.json()["checkout_url"] == "https://checkout.stripe.com/x"


def test_create_portal_session_without_subscription_returns_404(client: TestClient) -> None:
    response = client.post(
        "/v1/billing/portal-session",
        headers=AUTH,
        json={"return_url": "https://app/account"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_portal_session_returns_url(
    client: TestClient, subscriptions: InMemorySubscriptionRepository
) -> None:
    await subscriptions.upsert(
        Subscription(
            user_id=USER_ID,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=datetime.now(UTC),
        )
    )

    response = client.post(
        "/v1/billing/portal-session",
        headers=AUTH,
        json={"return_url": "https://app/account"},
    )

    assert response.status_code == 200
    assert response.json()["portal_url"] == "https://billing.stripe.com/x"


def test_webhook_processes_event_and_updates_subscription(
    client: TestClient,
    stripe_client: FakeStripeClient,
    subscriptions: InMemorySubscriptionRepository,
) -> None:
    stripe_client.queue_webhook_event(
        StripeWebhookEvent(
            stripe_event_id="evt_1",
            type="checkout.session.completed",
            stripe_customer_id="cus_1",
            user_id=USER_ID,
            stripe_subscription_id="sub_1",
            tier=None,
            status=None,
            current_period_end=None,
            raw_payload={"id": "evt_1"},
        )
    )

    response = client.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=fake"}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
