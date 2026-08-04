"""SQLAlchemy ORM models for the billing bounded context.

Maps `subscriptions` (docs/DATABASE.md §2.12 — a read replica of Stripe's
own state, keyed by `user_id`) and `stripe_events` (§2.13 — append-only
webhook idempotency log, keyed by Stripe's own event id).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_api.db import Base, UTCDateTime

_JSONType = JSON().with_variant(JSONB, "postgresql")


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    tier: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    current_period_end: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class StripeEventModel(Base):
    __tablename__ = "stripe_events"

    stripe_event_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(_JSONType, default=dict)
    processed_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
