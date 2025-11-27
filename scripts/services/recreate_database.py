#!/usr/bin/env python3
"""
Recreate database schema (drop all tables and create again) using SQLAlchemy metadata.

Uses current DatabaseConfig (SQLite by default; set DB_TYPE=postgresql and other
environment variables for PostgreSQL).
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    # Add src to Python path
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from loguru import logger
    from infrastructure.database.connection import DatabaseConfig, DatabaseManager
    from infrastructure.database.models import Base

    try:
        config = DatabaseConfig()
        logger.info(f"DB type: {config.db_type}")
        logger.info(f"Sync URL: {config.sync_database_url}")

        db = DatabaseManager(config)
        engine = db.sync_engine

        logger.warning("Dropping all tables...")
        Base.metadata.drop_all(engine)
        logger.info("All tables dropped.")

        logger.info("Creating all tables...")
        Base.metadata.create_all(engine)
        logger.info("All tables created.")

        return 0
    except Exception as e:
        logger.error(f"Failed to recreate database: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())






