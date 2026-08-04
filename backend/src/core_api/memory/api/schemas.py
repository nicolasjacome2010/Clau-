"""Pydantic request/response DTOs for the memory HTTP API.

The raw embedding vector is accepted on write (the caller — eventually
Reality Engine Agent 11 — computes it) but never echoed back wholesale on
read: responses expose metadata only, matching docs/UX_DESIGN.md pantalla
12's "Memoria" screen, which shows patterns/evidence, not raw vectors.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BiasObservationResponse(BaseModel):
    bias: str
    score: float
    occurrences: int


class UserBiasProfileResponse(BaseModel):
    biases: list[BiasObservationResponse]
    calibration_score: float
    updated_at: datetime | None


class RecordBiasObservationRequest(BaseModel):
    bias: str = Field(min_length=1, max_length=120)
    confidence: float = Field(ge=0.0, le=1.0)


class RecordCalibrationRequest(BaseModel):
    calibration_delta: float = Field(ge=-100.0, le=100.0)


class StoreMemoryRequest(BaseModel):
    summary_text: str = Field(min_length=1, max_length=500)
    embedding: list[float] = Field(min_length=1)
    decision_id: UUID | None = None


class MemoryResponse(BaseModel):
    id: UUID
    decision_id: UUID | None
    summary_text: str
    created_at: datetime
    similarity: float | None = None


class FindSimilarMemoriesRequest(BaseModel):
    embedding: list[float] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
