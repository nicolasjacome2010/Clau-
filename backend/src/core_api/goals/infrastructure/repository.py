"""SQLAlchemy implementation of the goals domain repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.goals.domain.entities import Goal
from core_api.goals.domain.repositories import GoalRepository
from core_api.goals.infrastructure.models import GoalModel


def _to_entity(model: GoalModel) -> Goal:
    return Goal(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        default_weight=model.default_weight,
        is_active=model.is_active,
        created_at=model.created_at,
    )


class SqlAlchemyGoalRepository(GoalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        model = await self._session.get(GoalModel, goal_id)
        return _to_entity(model) if model else None

    async def list_for_user(self, user_id: UUID, *, active_only: bool = True) -> list[Goal]:
        stmt = select(GoalModel).where(GoalModel.user_id == user_id)
        if active_only:
            stmt = stmt.where(GoalModel.is_active.is_(True))
        stmt = stmt.order_by(GoalModel.created_at)
        result = await self._session.execute(stmt)
        return [_to_entity(model) for model in result.scalars().all()]

    async def create(self, goal: Goal) -> Goal:
        model = GoalModel(
            id=goal.id,
            user_id=goal.user_id,
            name=goal.name,
            default_weight=goal.default_weight,
            is_active=goal.is_active,
            created_at=goal.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update(self, goal: Goal) -> Goal:
        model = await self._session.get(GoalModel, goal.id)
        if model is None:
            raise ValueError(f"Cannot update non-existent goal {goal.id}")
        model.name = goal.name
        model.default_weight = goal.default_weight
        model.is_active = goal.is_active
        await self._session.flush()
        return _to_entity(model)
