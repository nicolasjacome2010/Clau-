"""HTTP API for the goals bounded context.

Every endpoint operates on "my goals" — scoped implicitly to the caller's
authenticated identity, never to an arbitrary user_id supplied by the
client (see docs/ARCHITECTURE.md §11, defense in depth).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from core_api.dependencies import get_current_identity, get_goal_repository
from core_api.goals.api.schemas import CreateGoalRequest, GoalResponse, UpdateGoalRequest
from core_api.goals.application.use_cases import (
    CreateGoalInput,
    CreateGoalUseCase,
    ListActiveGoalsUseCase,
    UpdateGoalInput,
    UpdateGoalUseCase,
)
from core_api.goals.domain.entities import Goal
from core_api.goals.domain.exceptions import GoalNotFoundError
from core_api.goals.domain.repositories import GoalRepository
from core_api.identity.application.use_cases import AuthenticatedIdentity

router = APIRouter(prefix="/v1/goals", tags=["goals"])


def _to_response(goal: Goal) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        name=goal.name,
        default_weight=goal.default_weight,
        is_active=goal.is_active,
        created_at=goal.created_at,
    )


@router.get("", response_model=list[GoalResponse])
async def list_my_goals(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    goal_repository: Annotated[GoalRepository, Depends(get_goal_repository)],
) -> list[GoalResponse]:
    goals = await ListActiveGoalsUseCase(goal_repository).execute(identity.id)
    return [_to_response(goal) for goal in goals]


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: CreateGoalRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    goal_repository: Annotated[GoalRepository, Depends(get_goal_repository)],
) -> GoalResponse:
    goal = await CreateGoalUseCase(goal_repository).execute(
        CreateGoalInput(
            user_id=identity.id,
            name=payload.name,
            default_weight=payload.default_weight,
        )
    )
    return _to_response(goal)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    payload: UpdateGoalRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    goal_repository: Annotated[GoalRepository, Depends(get_goal_repository)],
) -> GoalResponse:
    try:
        goal = await UpdateGoalUseCase(goal_repository).execute(
            UpdateGoalInput(
                goal_id=goal_id,
                requesting_user_id=identity.id,
                name=payload.name,
                default_weight=payload.default_weight,
                is_active=payload.is_active,
            )
        )
    except GoalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found") from exc
    return _to_response(goal)
