"""Domain entities for the identity bounded context.

These are plain dataclasses with zero dependency on FastAPI, SQLAlchemy or
any other framework, per Clean Architecture (see docs/ARCHITECTURE.md §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    display_name: str | None
    locale: str
    onboarding_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def with_onboarding_completed(self, at: datetime | None = None) -> User:
        return replace(self, onboarding_completed_at=at or datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class UserProfile:
    user_id: UUID
    life_context: dict[str, Any] = field(default_factory=dict)
    risk_tolerance: int = 3
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        if not 1 <= self.risk_tolerance <= 5:
            raise ValueError("risk_tolerance must be between 1 and 5")
