"""Alembic environment.

Uses the async SQLAlchemy engine so migrations run against the exact same
driver (asyncpg) as the application, and pulls the DB URL from the app's own
Settings object rather than duplicating it in alembic.ini.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from core_api.config import get_settings
from core_api.db import Base, create_engine
from core_api.decisions.infrastructure import models as decisions_models  # noqa: F401
from core_api.goals.infrastructure import models as goals_models  # noqa: F401
from core_api.identity.infrastructure import models as identity_models  # noqa: F401
from core_api.memory.infrastructure import models as memory_models  # noqa: F401
from core_api.simulations.infrastructure import models as simulations_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_engine(get_settings().database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
