"""Alembic migration environment.

Supports both offline (SQL script) and online (live database) migration modes.
Uses the synchronous psycopg2 URL for migrations (asyncpg does not support
Alembic's synchronous connection model).

Run migrations:
    cd api/
    alembic upgrade head

Generate a new revision:
    alembic revision --autogenerate -m "description"
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make the app package importable from the api/ directory ───────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402 (after sys.path manipulation)
from app.database import Base  # noqa: E402
# Import all models so their metadata is populated before autogenerate runs
import app.models.db  # noqa: E402, F401

# Alembic Config object
config = context.config

# Use the synchronous DATABASE_SYNC_URL from our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData object with all ORM table definitions
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB and apply)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
