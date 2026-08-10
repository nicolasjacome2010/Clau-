"""HTTP API for the decisions bounded context.

Every endpoint operates on "my decisions", scoped to the caller's
authenticated identity (see goals/api/router.py for the same convention).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from core_api.decisions.api.schemas import (
    CreateDecisionRequest,
    DecisionDetailResponse,
    DecisionResponse,
    UpdateDecisionStatusRequest,
)
from core_api.decisions.application.use_cases import (
    CreateDecisionInput,
    CreateDecisionUseCase,
    GetUserDecisionUseCase,
    ListUserDecisionsUseCase,
    UpdateDecisionStatusInput,
    UpdateDecisionStatusUseCase,
)
from core_api.decisions.domain.entities import (
    Decision,
    DecisionStatus,
    InvalidStatusTransitionError,
)
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.dependencies import get_current_identity, get_decision_repository
from core_api.identity.application.use_cases import AuthenticatedIdentity

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


def _to_response(decision: Decision) -> DecisionResponse:
    return DecisionResponse(
        id=decision.id,
        title=decision.title,
        vertical=decision.vertical,
        status=decision.status,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )


def _to_detail_response(decision: Decision) -> DecisionDetailResponse:
    return DecisionDetailResponse(
        id=decision.id,
        title=decision.title,
        vertical=decision.vertical,
        status=decision.status,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
        raw_input=decision.raw_input,
    )


@router.get("", response_model=list[DecisionResponse])
async def list_my_decisions(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    status_filter: DecisionStatus | None = None,
) -> list[DecisionResponse]:
    decisions = await ListUserDecisionsUseCase(decision_repository).execute(
        identity.id, status=status_filter
    )
    return [_to_response(decision) for decision in decisions]


@router.post("", response_model=DecisionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: CreateDecisionRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> DecisionDetailResponse:
    decision = await CreateDecisionUseCase(decision_repository).execute(
        CreateDecisionInput(
            user_id=identity.id,
            raw_input=payload.raw_input,
            vertical=payload.vertical,
        )
    )
    return _to_detail_response(decision)


@router.get("/{decision_id}", response_model=DecisionDetailResponse)
async def get_decision(
    decision_id: UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> DecisionDetailResponse:
    try:
        decision = await GetUserDecisionUseCase(decision_repository).execute(
            decision_id, identity.id
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    return _to_detail_response(decision)


@router.patch("/{decision_id}/status", response_model=DecisionResponse)
async def update_decision_status(
    decision_id: UUID,
    payload: UpdateDecisionStatusRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> DecisionResponse:
    try:
        decision = await UpdateDecisionStatusUseCase(decision_repository).execute(
            UpdateDecisionStatusInput(
                decision_id=decision_id,
                requesting_user_id=identity.id,
                new_status=payload.status,
            )
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(decision)
