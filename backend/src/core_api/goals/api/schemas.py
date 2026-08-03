"""Pydantic request/response DTOs for the goals HTTP API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GoalResponse(BaseModel):
    id: UUID
    name: str
    default_weight: int
    is_active: bool
    created_at: datetime


class CreateGoalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    default_weight: int = Field(default=50, ge=0, le=100)


class UpdateGoalRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    default_weight: int | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None
