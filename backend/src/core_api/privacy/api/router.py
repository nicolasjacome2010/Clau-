"""HTTP API for the privacy bounded context.

Both endpoints operate on "me" and nothing else: there is no user id in
any path or body, so there is no shape of request that could export or
erase someone else's data by accident (same ownership rule as the rest of
the API, taken to its strictest form).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from core_api.billing.domain.repositories import SubscriptionRepository
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.dependencies import (
    get_current_identity,
    get_decision_outcome_repository,
    get_decision_repository,
    get_goal_repository,
    get_memory_embedding_repository,
    get_simulation_repository,
    get_subscription_repository,
    get_user_bias_profile_repository,
    get_user_profile_repository,
    get_user_repository,
)
from core_api.goals.domain.repositories import GoalRepository
from core_api.identity.application.use_cases import AuthenticatedIdentity
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.privacy.api.schemas import UserDataExportResponse
from core_api.privacy.application.use_cases import (
    EraseUserDataUseCase,
    ExportUserDataUseCase,
    PrivacyRepositories,
)
from core_api.privacy.domain.exceptions import ActiveSubscriptionError, UserNotFoundError
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository

router = APIRouter(prefix="/v1/privacy", tags=["privacy"])


def get_privacy_repositories(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    user_profile_repository: Annotated[UserProfileRepository, Depends(get_user_profile_repository)],
    goal_repository: Annotated[GoalRepository, Depends(get_goal_repository)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    simulation_repository: Annotated[SimulationRepository, Depends(get_simulation_repository)],
    decision_outcome_repository: Annotated[
        DecisionOutcomeRepository, Depends(get_decision_outcome_repository)
    ],
    user_bias_profile_repository: Annotated[
        UserBiasProfileRepository, Depends(get_user_bias_profile_repository)
    ],
    memory_embedding_repository: Annotated[
        MemoryEmbeddingRepository, Depends(get_memory_embedding_repository)
    ],
    subscription_repository: Annotated[
        SubscriptionRepository, Depends(get_subscription_repository)
    ],
) -> PrivacyRepositories:
    return PrivacyRepositories(
        users=user_repository,
        profiles=user_profile_repository,
        goals=goal_repository,
        decisions=decision_repository,
        simulations=simulation_repository,
        outcomes=decision_outcome_repository,
        bias_profiles=user_bias_profile_repository,
        memories=memory_embedding_repository,
        subscriptions=subscription_repository,
    )


@router.get("/export", response_model=UserDataExportResponse)
async def export_my_data(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    repositories: Annotated[PrivacyRepositories, Depends(get_privacy_repositories)],
) -> UserDataExportResponse:
    """Everything this service holds about the caller, in one document.

    Served inline rather than as an emailed job: at this scale the whole
    thing is a handful of rows, and a background job that mails a link is
    more moving parts (a queue, a mailer, a signed URL that expires) for a
    right the user should not have to wait on. If exports ever outgrow a
    request, that is the moment to add the job — not before.
    """
    try:
        export = await ExportUserDataUseCase(repositories).execute(identity.id)
    except UserNotFoundError as exc:
        # A valid token whose user row was never provisioned (that happens
        # on the first authenticated request, not at sign-in). There is
        # genuinely nothing to export, and saying so is better than an
        # empty document that reads like data loss.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No data to export yet"
        ) from exc
    return UserDataExportResponse(
        exported_at=export.exported_at,
        notes=export.notes,
        user=export.user,
        profile=export.profile,
        goals=export.goals,
        decisions=export.decisions,
        simulations=export.simulations,
        decision_outcomes=export.decision_outcomes,
        bias_profile=export.bias_profile,
        memories=export.memories,
        subscription=export.subscription,
    )


@router.delete("/data", status_code=status.HTTP_204_NO_CONTENT)
async def erase_my_data(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    repositories: Annotated[PrivacyRepositories, Depends(get_privacy_repositories)],
) -> None:
    """Erases the caller's data. There is no undo, and none is implied.

    A 404 here would be a strange answer to "delete my data" from a caller
    holding a valid token, so a user who doesn't exist yet gets the same
    204 as one who did: the requested state — no data — is the state that
    holds either way.
    """
    try:
        await EraseUserDataUseCase(repositories).execute(identity.id)
    except UserNotFoundError:
        return
    except ActiveSubscriptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cancel your subscription before deleting your data, so Stripe "
                "stops billing you"
            ),
        ) from exc
