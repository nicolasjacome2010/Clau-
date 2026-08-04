"""SQLAlchemy implementation of the billing domain repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.billing.domain.entities import (
    StripeEvent,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)
from core_api.billing.domain.repositories import StripeEventRepository, SubscriptionRepository
from core_api.billing.infrastructure.models import StripeEventModel, SubscriptionModel


def _to_subscription_entity(model: SubscriptionModel) -> Subscription:
    return Subscription(
        user_id=model.user_id,
        stripe_customer_id=model.stripe_customer_id,
        stripe_subscription_id=model.stripe_subscription_id,
        tier=SubscriptionTier(model.tier),
        status=SubscriptionStatus(model.status),
        current_period_end=model.current_period_end,
        updated_at=model.updated_at,
    )


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        model = await self._session.get(SubscriptionModel, user_id)
        return _to_subscription_entity(model) if model else None

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.stripe_customer_id == stripe_customer_id
            )
        )
        model = result.scalars().first()
        return _to_subscription_entity(model) if model else None

    async def upsert(self, subscription: Subscription) -> Subscription:
        model = await self._session.get(SubscriptionModel, subscription.user_id)
        if model is None:
            model = SubscriptionModel(user_id=subscription.user_id)
            self._session.add(model)
        model.stripe_customer_id = subscription.stripe_customer_id
        model.stripe_subscription_id = subscription.stripe_subscription_id
        model.tier = subscription.tier.value
        model.status = subscription.status.value
        model.current_period_end = subscription.current_period_end
        model.updated_at = subscription.updated_at
        await self._session.flush()
        return _to_subscription_entity(model)


class SqlAlchemyStripeEventRepository(StripeEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, stripe_event_id: str) -> bool:
        model = await self._session.get(StripeEventModel, stripe_event_id)
        return model is not None

    async def create(self, event: StripeEvent) -> StripeEvent:
        model = StripeEventModel(
            stripe_event_id=event.stripe_event_id,
            type=event.type,
            payload=event.payload,
            processed_at=event.processed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return event
