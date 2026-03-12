#!/usr/bin/env python3
"""
Inspect an existing PostgreSQL database and align known schema drift before baseline stamping.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from loguru import logger
from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"
BASELINE_REVISION = "0001"


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


def get_database_url() -> str:
    """Build a sync PostgreSQL URL from environment variables."""
    return (
        f"postgresql://{os.environ.get('DB_DB_USER', 'so_user')}:"
        f"{os.environ.get('DB_DB_PASSWORD', 'so_pass')}@"
        f"{os.environ.get('DB_DB_HOST', 'so_pg')}:"
        f"{os.environ.get('DB_DB_PORT', '5432')}/"
        f"{os.environ.get('DB_DB_NAME', 'so_uchet')}"
    )


def inspect_schema(database_url: str) -> list[str]:
    """Return human-readable mismatches between live DB and baseline contract."""
    engine = create_engine(database_url)
    inspector = inspect(engine)
    issues: list[str] = []

    read_positions_columns = {
        column["name"]: str(column["type"]) for column in inspector.get_columns("read_positions")
    }
    snapshot_columns = {
        column["name"]: column for column in inspector.get_columns("db_snapshots")
    }
    read_positions_uq_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints("read_positions")
        if constraint.get("name")
    }
    read_positions_index_names = {
        index.get("name") for index in inspector.get_indexes("read_positions") if index.get("name")
    }

    if read_positions_columns.get("purchase_price_amount") != "NUMERIC(18, 5)":
        issues.append("read_positions.purchase_price_amount must be NUMERIC(18, 5)")

    if read_positions_columns.get("margin_amount") != "NUMERIC(18, 5)":
        issues.append("read_positions.margin_amount must be NUMERIC(18, 5)")

    if "uq_read_positions_deal_position" not in read_positions_uq_names:
        issues.append("uq_read_positions_deal_position constraint is missing")

    if "ix_read_positions_deal_position" in read_positions_index_names:
        issues.append("legacy index ix_read_positions_deal_position must be removed")

    created_at_default = snapshot_columns.get("created_at", {}).get("default")
    normalized_default = str(created_at_default).lower() if created_at_default is not None else ""
    if "now()" not in normalized_default and "current_timestamp" not in normalized_default:
        issues.append("db_snapshots.created_at must have server default now()")

    return issues


def apply_known_fixes(database_url: str) -> None:
    """Apply safe schema fixes required before baseline stamping."""
    engine = create_engine(database_url)
    with engine.begin() as connection:
        duplicates = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT deal_id, position_number
                    FROM read_positions
                    GROUP BY deal_id, position_number
                    HAVING COUNT(*) > 1
                ) AS duplicate_positions
                """
            )
        ).scalar_one()
        if duplicates:
            raise RuntimeError(
                "Cannot add uq_read_positions_deal_position: duplicate deal_id/position_number rows exist"
            )

        logger.info("Applying numeric precision fix for read_positions")
        connection.execute(
            text(
                """
                ALTER TABLE read_positions
                ALTER COLUMN purchase_price_amount TYPE NUMERIC(18, 5),
                ALTER COLUMN margin_amount TYPE NUMERIC(18, 5)
                """
            )
        )

        logger.info("Restoring server default for db_snapshots.created_at")
        connection.execute(
            text(
                """
                ALTER TABLE db_snapshots
                ALTER COLUMN created_at SET DEFAULT now()
                """
            )
        )

        logger.info("Ensuring uq_read_positions_deal_position exists")
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'uq_read_positions_deal_position'
                    ) THEN
                        ALTER TABLE read_positions
                        ADD CONSTRAINT uq_read_positions_deal_position
                        UNIQUE (deal_id, position_number);
                    END IF;
                END $$;
                """
            )
        )

        logger.info("Removing legacy ix_read_positions_deal_position index")
        connection.execute(
            text("DROP INDEX IF EXISTS ix_read_positions_deal_position")
        )


def stamp_baseline(database_url: str) -> None:
    """Stamp the database with the single baseline revision."""
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    alembic_config = Config(str(MIGRATIONS_PATH / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(MIGRATIONS_PATH))
    command.stamp(alembic_config, BASELINE_REVISION, purge=True)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Inspect existing DB schema drift and optionally align/stamp the baseline."
    )
    parser.add_argument(
        "--apply-known-fixes",
        action="store_true",
        help="Apply known safe DDL fixes before re-checking the schema.",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Stamp baseline revision after the schema matches the canonical contract.",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    setup_logging()
    setup_postgresql_environment()
    database_url = get_database_url()

    logger.info("Inspecting database {}", database_url.rsplit("@", maxsplit=1)[-1])
    issues = inspect_schema(database_url)
    if issues:
        logger.warning("Schema drift detected:")
        for issue in issues:
            logger.warning(" - {}", issue)
    else:
        logger.info("Schema already matches the baseline contract")

    if args.apply_known_fixes and issues:
        apply_known_fixes(database_url)
        issues = inspect_schema(database_url)

    if issues:
        logger.error("Schema is not ready for baseline stamp")
        return 1

    if args.stamp:
        logger.info("Stamping existing database with baseline revision {}", BASELINE_REVISION)
        stamp_baseline(database_url)

    logger.info("Baseline alignment check completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
