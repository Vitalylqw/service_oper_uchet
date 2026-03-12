"""
Alembic environment configuration for Service Oper Uchet database.

Supports both PostgreSQL and SQLite databases with automatic configuration detection.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

# Add src to Python path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import project models and configuration
from infrastructure.database.models import Base
from infrastructure.database.connection import DatabaseConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_config() -> DatabaseConfig:
    """Get database configuration from environment."""
    return DatabaseConfig()


def get_database_url() -> str:
    """Get database URL for migrations."""
    # Allow explicit override for validation or temporary maintenance tasks.
    return os.getenv("ALEMBIC_DATABASE_URL", "postgresql://so_user:so_pass@so_pg:5432/so_uchet")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Enable automatic generation of migration scripts
        compare_type=True,
        compare_server_default=True,
        # Include comments in generated migrations
        include_comments=True,
        # Include indexes in generated migrations
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the URL from config file with environment-based URL
    config.set_main_option("sqlalchemy.url", get_database_url())
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


async def run_async_migrations() -> None:
    """Run migrations using async engine."""
    db_config = get_database_config()
    
    # Create async engine
    from sqlalchemy.ext.asyncio import create_async_engine
    async_engine = create_async_engine(db_config.async_database_url)
    
    async with async_engine.begin() as connection:
        await connection.run_sync(do_run_migrations)
    
    await async_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use sync migrations for PostgreSQL
    run_migrations_online()
