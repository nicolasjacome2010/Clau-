"""Pydantic request/response DTOs for the billing HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    current_period_end: datetime | None


class CreateCheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class CreatePortalSessionRequest(BaseModel):
    return_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str
