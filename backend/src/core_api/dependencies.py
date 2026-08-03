"""Shared FastAPI dependency-injection wiring.

Bounded contexts expose their own use cases; this module only wires the
cross-cutting concerns (DB session, authenticated identity) that every
router needs, plus the identity repositories since `identity` is the only
context implemented so far (see docs/PRD.md roadmap for what's next).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.auth.token_verifier import TokenVerificationError, TokenVerifier, VerifiedIdentity
from core_api.identity.application.use_cases import AuthenticatedIdentity
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository
from core_api.identity.infrastructure.repository import (
    SqlAlchemyUserProfileRepository,
    SqlAlchemyUserRepository,
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
