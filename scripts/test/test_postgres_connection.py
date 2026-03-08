#!/usr/bin/env python3
"""
Simple PostgreSQL connection test.

This script checks basic PostgreSQL connectivity without running synchronization.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def setup_logging() -> None:
    """Configure console logging for the script."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        colorize=False,
    )


def setup_postgresql_environment() -> None:
    """Load PostgreSQL settings from `config.env` into the environment."""
    config_file = PROJECT_ROOT / "config.env"

    if config_file.exists():
        logger.info("Loading PostgreSQL configuration from {}", config_file)

        with config_file.open("r", encoding="utf-8") as file_obj:
            for raw_line in file_obj:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
                    os.environ[key.lower()] = value

        os.environ["DB_TYPE"] = "postgresql"
        os.environ["db_type"] = "postgresql"
        os.environ["DB_DB_TYPE"] = "postgresql"
        os.environ["DB_DB_HOST"] = os.environ.get("DB_HOST", "so_pg")
        os.environ["DB_DB_PORT"] = os.environ.get("DB_PORT", "5432")
        os.environ["DB_DB_NAME"] = os.environ.get("DB_NAME", "so_uchet")
        os.environ["DB_DB_USER"] = os.environ.get("DB_USER", "so_user")
        os.environ["DB_DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "so_pass")

        logger.info("PostgreSQL environment configured")
        return

    logger.warning("Config file not found: {}", config_file)
    logger.info("Using default PostgreSQL settings")


async def test_postgres_connection() -> bool:
    """Run a basic connectivity and schema visibility check."""
    try:
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager

        logger.info("Testing PostgreSQL connection")

        config = DatabaseConfig()
        logger.info(
            "Database config: type={}, host={}, port={}, db={}",
            config.db_type,
            config.db_host,
            config.db_port,
            config.db_name,
        )

        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            result = await session.execute(text("SELECT 1 AS test_value"))
            test_value = result.scalar()

            if test_value != 1:
                logger.error("PostgreSQL connection check returned unexpected value")
                return False

            logger.info("PostgreSQL connection successful")

            version_result = await session.execute(text("SELECT version()"))
            logger.info("PostgreSQL version: {}", version_result.scalar())

            db_name_result = await session.execute(text("SELECT current_database()"))
            logger.info("Current database: {}", db_name_result.scalar())

            user_result = await session.execute(text("SELECT current_user"))
            logger.info("Current user: {}", user_result.scalar())

            tables_result = await session.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """
                )
            )
            tables = [row[0] for row in tables_result.fetchall()]
            logger.info("Available tables: {}", tables)
            return True

    except Exception as exc:
        logger.exception("PostgreSQL connection test failed: {}", exc)
        return False


async def main() -> int:
    """Script entrypoint."""
    setup_logging()
    setup_postgresql_environment()

    logger.info("Starting PostgreSQL connection test")
    success = await test_postgres_connection()

    if success:
        logger.info("PostgreSQL connection test passed")
        return 0

    logger.error("PostgreSQL connection test failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
