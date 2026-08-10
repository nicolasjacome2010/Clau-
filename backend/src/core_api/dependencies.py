"""Shared FastAPI dependency-injection wiring.

Bounded contexts expose their own use cases; this module only wires the
cross-cutting concerns (DB session, authenticated identity) every router
needs, plus a thin repository-provider function per bounded context. Use
cases are instantiated in each context's own router, not here — this file
only wires *what a repository needs to exist* (a DB session), not *how a
use case uses it*.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.auth.token_verifier import TokenVerificationError, TokenVerifier, VerifiedIdentity
from core_api.billing.domain.repositories import StripeEventRepository, SubscriptionRepository
from core_api.billing.domain.stripe_port import StripeClient
from core_api.billing.infrastructure.repository import (
    SqlAlchemyStripeEventRepository,
    SqlAlchemySubscriptionRepository,
)
from core_api.crypto import FieldEncryptor
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.decisions.infrastructure.repository import SqlAlchemyDecisionRepository
from core_api.goals.domain.repositories import GoalRepository
from core_api.goals.infrastructure.repository import SqlAlchemyGoalRepository
from core_api.identity.application.use_cases import AuthenticatedIdentity
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository
from core_api.identity.infrastructure.repository import (
    SqlAlchemyUserProfileRepository,
    SqlAlchemyUserRepository,
)
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.memory.infrastructure.repository import (
    SqlAlchemyMemoryEmbeddingRepository,
    SqlAlchemyUserBiasProfileRepository,
)
from core_api.simulations.domain.reality_engine_port import RealityEngineClient
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository
from core_api.simulations.infrastructure.repository import (
    SqlAlchemyDecisionOutcomeRepository,
    SqlAlchemySimulationRepository,
)

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_token_verifier(request: Request) -> TokenVerifier:
    # `Starlette.State` is intentionally untyped (it's a generic bag set up
    # in main.py's lifespan), so this cast documents the real contract.
    return cast(TokenVerifier, request.app.state.token_verifier)


def get_field_encryptor(request: Request) -> FieldEncryptor:
    return cast(FieldEncryptor, request.app.state.field_encryptor)


def get_reality_engine_client(request: Request) -> RealityEngineClient:
    return cast(RealityEngineClient, request.app.state.reality_engine_client)


def get_stripe_client(request: Request) -> StripeClient:
    return cast(StripeClient, request.app.state.stripe_client)


async def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthenticatedIdentity:
    try:
        verified: VerifiedIdentity = await verifier.verify(credentials.credentials)
    except TokenVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return AuthenticatedIdentity(id=verified.id, email=verified.email)


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_user_profile_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileRepository:
    return SqlAlchemyUserProfileRepository(session)


def get_goal_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoalRepository:
    return SqlAlchemyGoalRepository(session)


def get_decision_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    encryptor: Annotated[FieldEncryptor, Depends(get_field_encryptor)],
) -> DecisionRepository:
    return SqlAlchemyDecisionRepository(session, encryptor)


def get_simulation_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SimulationRepository:
    return SqlAlchemySimulationRepository(session)


def get_decision_outcome_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DecisionOutcomeRepository:
    return SqlAlchemyDecisionOutcomeRepository(session)


def get_user_bias_profile_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserBiasProfileRepository:
    return SqlAlchemyUserBiasProfileRepository(session)


def get_memory_embedding_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MemoryEmbeddingRepository:
    return SqlAlchemyMemoryEmbeddingRepository(session)


def get_subscription_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionRepository:
    return SqlAlchemySubscriptionRepository(session)


def get_stripe_event_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StripeEventRepository:
    return SqlAlchemyStripeEventRepository(session)
