"""Pydantic response DTOs for the privacy HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UserDataExportResponse(BaseModel):
    """The export document, one section per bounded context.

    Sections are loose `dict`s on purpose: this is a copy of the user's own
    records, and pinning each one to a typed schema here would mean two
    definitions of the same shape drifting apart — the owning context's
    entity is the definition.
    """

    exported_at: datetime
    notes: list[str]
    user: dict[str, Any]
    profile: dict[str, Any] | None
    goals: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    simulations: list[dict[str, Any]]
    decision_outcomes: list[dict[str, Any]]
    bias_profile: dict[str, Any] | None
    memories: list[dict[str, Any]]
    subscription: dict[str, Any] | None
