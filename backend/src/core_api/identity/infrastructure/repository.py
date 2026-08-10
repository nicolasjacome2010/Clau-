"""SQLAlchemy implementations of the identity domain repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.identity.domain.entities import User, UserProfile
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository
from core_api.identity.infrastructure.models import UserModel, UserProfileModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        display_name=model.display_name,
        locale=model.locale,
        onboarding_completed_at=model.onboarding_completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_profile_entity(model: UserProfileModel) -> UserProfile:
    return UserProfile(
        user_id=model.user_id,
        life_context=model.life_context,
        risk_tolerance=model.risk_tolerance,
        timezone=model.timezone,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            locale=user.locale,
            onboarding_completed_at=user.onboarding_completed_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"Cannot update non-existent user {user.id}")
        model.email = user.email
        model.display_name = user.display_name
        model.locale = user.locale
        model.onboarding_completed_at = user.onboarding_completed_at
        model.updated_at = user.updated_at
        await self._session.flush()
        return _to_entity(model)

    async def delete(self, user_id: UUID) -> bool:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True


class SqlAlchemyUserProfileRepository(UserProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return _to_profile_entity(model) if model else None

    async def upsert(self, profile: UserProfile) -> UserProfile:
        dialect = self._session.bind.dialect.name if self._session.bind else "postgresql"
        values = {
            "user_id": profile.user_id,
            "life_context": profile.life_context,
            "risk_tolerance": profile.risk_tolerance,
            "timezone": profile.timezone,
        }
        if dialect == "postgresql":
            stmt = pg_insert(UserProfileModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[UserProfileModel.user_id],
                set_={
                    "life_context": stmt.excluded.life_context,
                    "risk_tolerance": stmt.excluded.risk_tolerance,
                    "timezone": stmt.excluded.timezone,
                },
            )
            await self._session.execute(stmt)
        else:
            # Portable fallback for dialects without native upsert (e.g. the
            # sqlite backend used in fast infrastructure tests, see
            # tests/integration/identity/test_repository.py).
            existing = await self._session.get(UserProfileModel, profile.user_id)
            if existing is None:
                self._session.add(UserProfileModel(**values))
            else:
                existing.life_context = profile.life_context
                existing.risk_tolerance = profile.risk_tolerance
                existing.timezone = profile.timezone
        await self._session.flush()
        return profile
