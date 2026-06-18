import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from src.config import settings
from src.db.models import *  # noqa: F401, F403 — import all models so Alembic detects schema changes

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at your SQLModel models' metadata for autogenerate
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (no live DB connection).
    Generates a SQL script that can be applied manually.
    """
    assert settings.DATABASE_URL is not None, "DATABASE_URL must be set"
    url = settings.DATABASE_URL
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


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg)."""
    assert settings.DATABASE_URL is not None, "DATABASE_URL must be set"
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
