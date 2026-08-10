"""SQLAlchemy ORM models for the identity bounded context.

Maps 1:1 to the `users` / `user_profiles` tables defined in
docs/DATABASE.md §2.1-2.2. These are infrastructure details — domain code
never imports from this module directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_api.db import Base, UTCDateTime

_JSONType = JSON().with_variant(JSONB, "postgresql")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    locale: Mapped[str] = mapped_column(String, default="es")
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    life_context: Mapped[dict[str, Any]] = mapped_column(_JSONType, default=dict)
    risk_tolerance: Mapped[int] = mapped_column(SmallInteger, default=3)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
