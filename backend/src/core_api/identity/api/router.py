"""HTTP API for the identity bounded context."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from core_api.dependencies import (
    get_current_identity,
    get_user_profile_repository,
    get_user_repository,
)
from core_api.identity.api.schemas import (
    UpdateUserProfileRequest,
    UserProfileResponse,
    UserResponse,
)
from core_api.identity.application.use_cases import (
    AuthenticatedIdentity,
    GetOrCreateUserUseCase,
    UpdateUserProfileInput,
    UpdateUserProfileUseCase,
)
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository

router = APIRouter(prefix="/v1/users", tags=["identity"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    profile_repository: Annotated[UserProfileRepository, Depends(get_user_profile_repository)],
) -> UserResponse:
    user = await GetOrCreateUserUseCase(user_repository).execute(identity)
    profile = await profile_repository.get_by_user_id(user.id)
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        locale=user.locale,
        onboarding_completed_at=user.onboarding_completed_at,
        life_context=profile.life_context if profile else {},
        risk_tolerance=profile.risk_tolerance if profile else 3,
        timezone=profile.timezone if profile else "UTC",
    )


@router.patch("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UpdateUserProfileRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    profile_repository: Annotated[UserProfileRepository, Depends(get_user_profile_repository)],
) -> UserProfileResponse:
    # Ensures the domain User row exists (JIT provisioning) before a profile
    # can be attached to it — a profile without a user would violate the FK
    # defined in docs/DATABASE.md §2.2.
    await GetOrCreateUserUseCase(user_repository).execute(identity)

    use_case = UpdateUserProfileUseCase(user_repository, profile_repository)
    profile = await use_case.execute(
        UpdateUserProfileInput(
            user_id=identity.id,
            life_context=payload.life_context,
            risk_tolerance=payload.risk_tolerance,
            timezone=payload.timezone,
        )
    )
    return UserProfileResponse(
        user_id=profile.user_id,
        life_context=profile.life_context,
        risk_tolerance=profile.risk_tolerance,
        timezone=profile.timezone,
    )
