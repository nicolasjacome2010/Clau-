"""Pydantic request/response DTOs for the identity HTTP API.

These are adapters at the boundary — domain entities never cross this line
directly (see docs/ARCHITECTURE.md §4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    locale: str
    onboarding_completed_at: datetime | None
    life_context: dict[str, Any]
    risk_tolerance: int
    timezone: str


class UpdateUserProfileRequest(BaseModel):
    life_context: dict[str, Any] | None = None
    risk_tolerance: int | None = Field(default=None, ge=1, le=5)
    timezone: str | None = None


class UserProfileResponse(BaseModel):
    user_id: UUID
    life_context: dict[str, Any]
    risk_tolerance: int
    timezone: str
