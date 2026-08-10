from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.crypto import FernetFieldEncryptor
from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.infrastructure.models import DecisionModel
from core_api.decisions.infrastructure.repository import SqlAlchemyDecisionRepository
from core_api.identity.domain.entities import User
from core_api.identity.infrastructure.repository import SqlAlchemyUserRepository


async def _create_user(session: AsyncSession) -> User:
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        display_name=None,
        locale="es",
        onboarding_completed_at=None,
        created_at=now,
        updated_at=now,
    )
    return await SqlAlchemyUserRepository(session).create(user)


def _encryptor() -> FernetFieldEncryptor:
    return FernetFieldEncryptor(Fernet.generate_key().decode())


@pytest.mark.asyncio
async def test_create_and_get_decision_round_trips_and_decrypts(
    sqlite_session: AsyncSession,
) -> None:
    user = await _create_user(sqlite_session)
    repo = SqlAlchemyDecisionRepository(sqlite_session, _encryptor())
    now = datetime.now(UTC)
    decision = Decision(
        id=uuid4(),
        user_id=user.id,
        title="¿Debo aceptar la oferta?",
        vertical=DecisionVertical.CAREER,
        status=DecisionStatus.DRAFT,
        raw_input="Texto sensible de la decisión del usuario",
        created_at=now,
        updated_at=now,
    )

    await repo.create(decision)
    fetched = await repo.get_by_id(decision.id)

    assert fetched == decision


@pytest.mark.asyncio
async def test_raw_input_is_never_stored_in_plaintext(sqlite_session: AsyncSession) -> None:
    user = await _create_user(sqlite_session)
    repo = SqlAlchemyDecisionRepository(sqlite_session, _encryptor())
    secret_text = "no debería aparecer en texto plano en la base de datos"
    decision = Decision(
        id=uuid4(),
        user_id=user.id,
        title="t",
        vertical=DecisionVertical.CAREER,
        status=DecisionStatus.DRAFT,
        raw_input=secret_text,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await repo.create(decision)

    stmt = select(DecisionModel).where(DecisionModel.id == decision.id)
    result = await sqlite_session.execute(stmt)
    stored = result.scalar_one()

    assert secret_text.encode() not in stored.raw_input_encrypted


@pytest.mark.asyncio
async def test_list_for_user_filters_by_status(sqlite_session: AsyncSession) -> None:
    user = await _create_user(sqlite_session)
    repo = SqlAlchemyDecisionRepository(sqlite_session, _encryptor())
    now = datetime.now(UTC)
    draft = await repo.create(
        Decision(
            id=uuid4(),
            user_id=user.id,
            title="draft",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.DRAFT,
            raw_input="a",
            created_at=now,
            updated_at=now,
        )
    )
    await repo.create(
        Decision(
            id=uuid4(),
            user_id=user.id,
            title="completed",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.COMPLETED,
            raw_input="b",
            created_at=now,
            updated_at=now,
        )
    )

    only_drafts = await repo.list_for_user(user.id, status=DecisionStatus.DRAFT)

    assert [d.id for d in only_drafts] == [draft.id]


@pytest.mark.asyncio
async def test_update_persists_new_status_and_raw_input(sqlite_session: AsyncSession) -> None:
    user = await _create_user(sqlite_session)
    repo = SqlAlchemyDecisionRepository(sqlite_session, _encryptor())
    now = datetime.now(UTC)
    decision = await repo.create(
        Decision(
            id=uuid4(),
            user_id=user.id,
            title="t",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.DRAFT,
            raw_input="original",
            created_at=now,
            updated_at=now,
        )
    )

    updated = decision.with_status(DecisionStatus.CLARIFYING, at=datetime.now(UTC))
    await repo.update(updated)
    fetched = await repo.get_by_id(decision.id)

    assert fetched is not None
    assert fetched.status == DecisionStatus.CLARIFYING
