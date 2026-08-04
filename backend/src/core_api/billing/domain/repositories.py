"""Repository interfaces (ports) for the billing bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core_api.billing.domain.entities import StripeEvent, Subscription


class SubscriptionRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Subscription | None: ...

    @abstractmethod
    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Subscription | None: ...

    @abstractmethod
    async def upsert(self, subscription: Subscription) -> Subscription: ...


class StripeEventRepository(ABC):
    """`stripe_events` is append-only (docs/DATABASE.md §2.13) — there is
    no `update`/`delete`, only `create` and the `exists` idempotency check.
    """

    @abstractmethod
    async def exists(self, stripe_event_id: str) -> bool: ...

    @abstractmethod
    async def create(self, event: StripeEvent) -> StripeEvent: ...
