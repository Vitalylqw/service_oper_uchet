#!/usr/bin/env python3
"""Initialize (or recreate) the SQLite development database using SQLAlchemy models.

Usage (PowerShell / CMD):

    python scripts/services/init_db_from_models.py                  # создать, если БД отсутствует
    python scripts/services/init_db_from_models.py --reset          # удалить существующий файл и создать заново
    python scripts/services/init_db_from_models.py --path my.db     # использовать другой путь

По умолчанию создаёт файл *data/service_oper_uchet.sqlite* и все таблицы,
определённые в *infrastructure.database.models*.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# ────────────────────────────────────────────────────────────────
# Настройка путей
# ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # scripts/ → project root
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

# 🔄 Импорт после корректировки sys.path
from infrastructure.database.models import Base  # noqa: E402  pylint: disable=wrong-import-position

# DatabaseConfig нужен для централизованной конфигурации (может подтягивать env)
from infrastructure.database.connection import DatabaseConfig  # noqa: E402  pylint: disable=wrong-import-position


# ────────────────────────────────────────────────────────────────
# Функции
# ────────────────────────────────────────────────────────────────

def init_database(db_path: Path, reset: bool = False) -> None:
    """Create all tables in the SQLite database.

    Args:
        db_path: Path to SQLite file.
        reset: If *True* – delete existing file before creation.
    """
    if reset and db_path.exists():
        db_path.unlink()
        logger.info(f"📁 Deleted existing database file: {db_path}")

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # ⏱  Настраиваем sync-engine (для create_all достаточно синхронного движка)
    engine = create_engine(f"sqlite:///{db_path}")

    try:
        Base.metadata.create_all(engine)
        logger.success("✅ All tables created successfully!")
    except SQLAlchemyError as exc:
        logger.error(f"❌ Failed to create tables: {exc}")
        raise


# ────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create SQLite database from SQLAlchemy models",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing DB file before creation",
    )
    parser.add_argument(
        "--path",
        default="data/service_oper_uchet.sqlite",
        help="Path to SQLite database file (default: data/service_oper_uchet.sqlite)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)

    # Если переменные окружения БД ещё не заданы – выставим по умолчанию.
    os.environ.setdefault("DB_TYPE", "sqlite")
    os.environ.setdefault("DB_SQLITE_DB_PATH", args.path)

    # Печать итоговой конфигурации (debug-friendly)
    cfg = DatabaseConfig()
    logger.info(
        "Using DB config – type: {cfg.db_type}, path: {cfg.sqlite_db_path}",
    )

    db_path = Path(args.path)
    init_database(db_path, args.reset)


if __name__ == "__main__":
    main()
