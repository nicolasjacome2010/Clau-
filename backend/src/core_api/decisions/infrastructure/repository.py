"""SQLAlchemy implementation of the decisions domain repository.

Encrypts `raw_input` before it touches the database and decrypts it on the
way out, per docs/DATABASE.md §5 — this is the only place in the codebase
that should ever see `raw_input_encrypted` as ciphertext.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.crypto import FieldEncryptor
from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.decisions.infrastructure.models import DecisionModel


class SqlAlchemyDecisionRepository(DecisionRepository):
    def __init__(self, session: AsyncSession, encryptor: FieldEncryptor) -> None:
        self._session = session
        self._encryptor = encryptor

    def _to_entity(self, model: DecisionModel) -> Decision:
        return Decision(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            vertical=DecisionVertical(model.vertical),
            status=DecisionStatus(model.status),
            raw_input=self._encryptor.decrypt(model.raw_input_encrypted),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, decision_id: UUID) -> Decision | None:
        model = await self._session.get(DecisionModel, decision_id)
        return self._to_entity(model) if model else None

    async def list_for_user(
        self, user_id: UUID, *, status: DecisionStatus | None = None
    ) -> list[Decision]:
        stmt = select(DecisionModel).where(DecisionModel.user_id == user_id)
        if status is not None:
            stmt = stmt.where(DecisionModel.status == status.value)
        stmt = stmt.order_by(DecisionModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(model) for model in result.scalars().all()]

    async def create(self, decision: Decision) -> Decision:
        model = DecisionModel(
            id=decision.id,
            user_id=decision.user_id,
            title=decision.title,
            vertical=decision.vertical.value,
            status=decision.status.value,
            raw_input_encrypted=self._encryptor.encrypt(decision.raw_input),
            created_at=decision.created_at,
            updated_at=decision.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, decision: Decision) -> Decision:
        model = await self._session.get(DecisionModel, decision.id)
        if model is None:
            raise ValueError(f"Cannot update non-existent decision {decision.id}")
        model.title = decision.title
        model.status = decision.status.value
        model.raw_input_encrypted = self._encryptor.encrypt(decision.raw_input)
        model.updated_at = decision.updated_at
        await self._session.flush()
        return self._to_entity(model)
