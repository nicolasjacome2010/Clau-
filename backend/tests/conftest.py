from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.db import Base, create_engine, create_session_factory
from core_api.identity.infrastructure import models as identity_models  # noqa: F401


@pytest_asyncio.fixture
async def sqlite_session() -> AsyncIterator[AsyncSession]:
    """A fresh in-memory SQLite database per test.

    Used for infrastructure-layer tests that need a *real* ORM round-trip
    (autoincrement defaults, constraints, upsert fallback path) without the
    cost/flakiness of spinning up Postgres in CI for a single-service test
    suite. Cross-database portability is verified explicitly in
    `identity/infrastructure/repository.py` (see the dialect branch in
    `SqlAlchemyUserProfileRepository.upsert`).
    """
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session

    await engine.dispose()
