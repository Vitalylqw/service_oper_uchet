#!/usr/bin/env python3
"""
Reset SQLite database for the project.

Performs a *clean* recreation (variant A):
1. Backs up the existing SQLite file to the *data/backup* directory with a timestamp.
2. Creates a fresh database with the current SQLAlchemy metadata (all tables).

Usage (Windows)::

    python scripts/database/reset_database.py

A wrapper *reset_database.bat* is also added for convenience.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from loguru import logger

from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.models import Base

BACKUP_DIR = Path("data/backup")
DB_PATH = Path("data/service_oper_uchet.sqlite")


async def backup_existing_db() -> None:
    """Move the current DB file to *data/backup* preserving it with a timestamp."""
    if not DB_PATH.exists():
        logger.info("Database file not found – nothing to back up.")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"service_oper_uchet_{timestamp}.sqlite"

    DB_PATH.rename(backup_path)
    logger.info(f"Existing database backed up to: {backup_path}")


async def create_fresh_db() -> None:
    """Create a brand-new SQLite database with the current schema."""
    # Ensure *data* directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    config = DatabaseConfig()
    # Safety check: we support only SQLite here
    if config.db_type != "sqlite":
        raise RuntimeError(
            "reset_database.py is intended for SQLite development environment only."
        )

    db_manager = DatabaseManager(config)
    logger.info("Creating fresh SQLite database with latest schema…")

    # Create all tables synchronously via the sync engine
    Base.metadata.create_all(db_manager.sync_engine)

    # Quick connectivity test
    if not await db_manager.test_connection():
        raise RuntimeError("Failed to connect to freshly created database")

    logger.info("✅ Fresh database created and verified successfully.")


async def main() -> None:
    logger.info("🚀 Resetting SQLite database (clean recreation, variant A)…")

    await backup_existing_db()
    await create_fresh_db()

    logger.info("🎉 Database reset complete – you are ready to rerun integration tests.")


if __name__ == "__main__":
    asyncio.run(main())
