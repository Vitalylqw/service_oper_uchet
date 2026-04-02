"""Common helpers for the `so-uchet` CLI."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from loguru import logger

try:
    from infrastructure.config.env_loader import load_runtime_env
    from infrastructure.database.connection import DatabaseConfig, DatabaseManager
except ImportError:  # pragma: no cover - fallback for repo-local imports
    from src.infrastructure.config.env_loader import load_runtime_env
    from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"
ALIGN_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "services" / "align_existing_db_to_baseline.py"


def configure_logging(level: str) -> None:
    """Configure console logging for CLI commands."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        colorize=False,
    )


def initialize_runtime(log_level: str, env_file: str | None = None) -> Path:
    """Initialize logging and environment for the CLI process."""
    configure_logging(log_level)
    env_path = load_runtime_env(env_file)
    logger.debug("CLI runtime initialized with env file {}", env_path)
    return env_path


def build_database_manager() -> DatabaseManager:
    """Create a database manager using the active environment."""
    return DatabaseManager(DatabaseConfig())


def run_async(coro):
    """Run a coroutine in a fresh event loop."""
    return asyncio.run(coro)


def build_alembic_config() -> Config:
    """Create Alembic config bound to the active database URL."""
    db_config = DatabaseConfig()
    os.environ["ALEMBIC_DATABASE_URL"] = db_config.sync_database_url

    alembic_config = Config(str(MIGRATIONS_PATH / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(MIGRATIONS_PATH))
    return alembic_config


def run_alembic_upgrade(revision: str = "head") -> None:
    """Run Alembic upgrade for the configured database."""
    logger.info("Running alembic upgrade {}", revision)
    command.upgrade(build_alembic_config(), revision)


def run_align_script(apply_fixes: bool, stamp: bool) -> int:
    """Execute the existing baseline alignment script."""
    command_args = [sys.executable, str(ALIGN_SCRIPT_PATH)]
    if apply_fixes:
        command_args.append("--apply-known-fixes")
    if stamp:
        command_args.append("--stamp")

    logger.info("Running schema alignment script")
    completed = subprocess.run(
        command_args,
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
        check=False,
    )
    return completed.returncode
