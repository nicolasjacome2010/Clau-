from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.billing.domain.entities import (
    StripeEvent,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)
from core_api.billing.infrastructure.repository import (
    SqlAlchemyStripeEventRepository,
    SqlAlchemySubscriptionRepository,
)
from core_api.identity.domain.entities import User
from core_api.identity.infrastructure.repository import SqlAlchemyUserRepository


async def _make_user(session: AsyncSession) -> User:
    now = datetime.now(UTC)
    return await SqlAlchemyUserRepository(session).create(
        User(
            id=uuid4(),
            email=f"{uuid4()}@example.com",
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_upsert_creates_then_updates_subscription(sqlite_session: AsyncSession) -> None:
    user = await _make_user(sqlite_session)
    repo = SqlAlchemySubscriptionRepository(sqlite_session)
    now = datetime.now(UTC)

    created = await repo.upsert(
        Subscription(
            user_id=user.id,
            stripe_customer_id="cus_1",
            stripe_subscription_id=None,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )
    assert created.tier == SubscriptionTier.FREE

    later = datetime(2026, 9, 1, tzinfo=UTC)
    updated = await repo.upsert(
        Subscription(
            user_id=user.id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=later,
            updated_at=later,
        )
    )
    assert updated.tier == SubscriptionTier.PRO
    assert updated.stripe_subscription_id == "sub_1"

    fetched = await repo.get_by_user_id(user.id)
    assert fetched is not None
    assert fetched.tier == SubscriptionTier.PRO
    assert fetched.current_period_end == later

    by_customer = await repo.get_by_stripe_customer_id("cus_1")
    assert by_customer is not None
    assert by_customer.user_id == user.id


@pytest.mark.asyncio
async def test_get_by_user_id_returns_none_when_missing(sqlite_session: AsyncSession) -> None:
    repo = SqlAlchemySubscriptionRepository(sqlite_session)

    assert await repo.get_by_user_id(uuid4()) is None
    assert await repo.get_by_stripe_customer_id("cus_missing") is None


@pytest.mark.asyncio
async def test_stripe_event_create_and_exists_round_trip(sqlite_session: AsyncSession) -> None:
    repo = SqlAlchemyStripeEventRepository(sqlite_session)
    now = datetime.now(UTC)

    assert await repo.exists("evt_1") is False

    await repo.create(
        StripeEvent(
            stripe_event_id="evt_1",
            type="customer.subscription.updated",
            payload={"id": "evt_1"},
            processed_at=now,
        )
    )

    assert await repo.exists("evt_1") is True
