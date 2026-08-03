"""Pydantic request/response DTOs for the decisions HTTP API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from core_api.decisions.domain.entities import DecisionStatus, DecisionVertical


class DecisionResponse(BaseModel):
    id: UUID
    title: str
    vertical: DecisionVertical
    status: DecisionStatus
    created_at: datetime
    updated_at: datetime


class DecisionDetailResponse(DecisionResponse):
    raw_input: str


class CreateDecisionRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=4000)
    vertical: DecisionVertical


class UpdateDecisionStatusRequest(BaseModel):
    status: DecisionStatus
