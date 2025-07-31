"""Add totals validation columns to read_deals.

Usage (PowerShell):
    python scripts/database/migrations/20250801_add_totals_validation_columns.py
    # или указать БД явно
    python scripts/database/migrations/20250801_add_totals_validation_columns.py postgresql://user:pass@host/db

Скрипт читает переменную окружения DATABASE_URL, либо принимает URL первым аргументом.
Поддерживаются:
    • PostgreSQL – обычные ALTER TABLE ADD COLUMN ...
    • SQLite     – простые ALTER TABLE (каждый ADD отдельно)

Колонки добавляются, только если их ещё нет, поэтому скрипт идемпотентен и безопасен для повторного запуска.
"""
from __future__ import annotations

import os
import sys
from typing import List

from loguru import logger
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.engine import Engine

# Колонки в формате (<имя>, <DDL>)
COLUMNS: List[tuple[str, str]] = [
    ("source_revenue_amount", "NUMERIC(15,2)"),
    ("source_margin_amount", "NUMERIC(15,2)"),
    ("source_cost_amount", "NUMERIC(15,2)"),
    ("calc_revenue_amount", "NUMERIC(15,2) DEFAULT 0"),
    ("calc_margin_amount", "NUMERIC(15,2) DEFAULT 0"),
    ("calc_cost_amount", "NUMERIC(15,2) DEFAULT 0"),
    ("revenue_mismatch", "NUMERIC(15,2) DEFAULT 0"),
    ("margin_mismatch", "NUMERIC(15,2) DEFAULT 0"),
    ("cost_mismatch", "NUMERIC(15,2) DEFAULT 0"),
    ("has_totals_error", "BOOLEAN DEFAULT FALSE"),
]

def _column_exists(engine: Engine, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("read_deals")]
    return column_name in columns


def _apply_postgres(engine: Engine) -> None:
    added: list[str] = []
    with engine.begin() as conn:
        for name, ddl in COLUMNS:
            if not _column_exists(engine, name):
                logger.info(f"Adding column {name} (PostgreSQL)")
                conn.execute(text(f"ALTER TABLE read_deals ADD COLUMN {name} {ddl};"))
                added.append(name)
    logger.success(f"PostgreSQL migration complete. Added: {added if added else 'none'}")


def _apply_sqlite(engine: Engine) -> None:
    added: list[str] = []
    with engine.begin() as conn:
        for name, ddl in COLUMNS:
            if not _column_exists(engine, name):
                logger.info(f"Adding column {name} (SQLite)")
                conn.execute(text(f"ALTER TABLE read_deals ADD COLUMN {name} {ddl}"))
                added.append(name)
    logger.success(f"SQLite migration complete. Added: {added if added else 'none'}")


def main() -> None:
    db_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("DATABASE_URL", "sqlite:///data/service_oper_uchet.sqlite")
    engine = create_engine(db_url, isolation_level="AUTOCOMMIT", future=True)

    logger.info(f"Running migration on {db_url}")

    if engine.dialect.name == "postgresql":
        _apply_postgres(engine)
    elif engine.dialect.name == "sqlite":
        _apply_sqlite(engine)
    else:
        logger.error(f"Unsupported dialect: {engine.dialect.name}")
        sys.exit(1)

    logger.success("Migration finished ✓")


if __name__ == "__main__":
    main()
