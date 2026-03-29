"""Common helpers for the `so-uchet` CLI."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from loguru import logger

try:
    from infrastructure.database.connection import DatabaseConfig, DatabaseManager
except ImportError:  # pragma: no cover - fallback for repo-local imports
    from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"
ALIGN_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "services" / "align_existing_db_to_baseline.py"
DEFAULT_ENV_FILE = PROJECT_ROOT / "config.env"

_DOTENV_LOADED = False


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


def load_runtime_env(env_file: str | None = None) -> Path:
    """Load runtime environment and promote legacy DB variables."""
    global _DOTENV_LOADED

    if _DOTENV_LOADED:
        return Path(os.environ.get("ENV_FILE", str(DEFAULT_ENV_FILE))).resolve()

    if os.getenv("APP_DISABLE_DOTENV") == "1":
        logger.debug("dotenv loading disabled via APP_DISABLE_DOTENV=1")
        _DOTENV_LOADED = True
        return Path(os.environ.get("ENV_FILE", str(DEFAULT_ENV_FILE))).resolve()

    configured_env_file = env_file or os.getenv("ENV_FILE") or str(DEFAULT_ENV_FILE)
    env_path = Path(configured_env_file).resolve()

    os.environ.setdefault("ENV_FILE", str(env_path))

    try:
        loaded = load_dotenv(dotenv_path=str(env_path), override=False)
        logger.debug(
            "dotenv loaded: file={} loaded={} override={}",
            env_path,
            loaded,
            False,
        )
    except Exception as exc:
        logger.debug("dotenv load failed for {}: {}", env_path, exc)

    _promote_legacy_database_env()
    _DOTENV_LOADED = True
    return env_path


def _promote_legacy_database_env() -> None:
    """Map legacy `config.env` variables to `DatabaseConfig` names."""
    mapping = {
        "DB_TYPE": "DB_DB_TYPE",
        "DB_HOST": "DB_DB_HOST",
        "DB_PORT": "DB_DB_PORT",
        "DB_NAME": "DB_DB_NAME",
        "DB_USER": "DB_DB_USER",
        "DB_PASSWORD": "DB_DB_PASSWORD",
        "DB_POOL_SIZE": "DB_DB_POOL_SIZE",
        "DB_POOL_MAX_OVERFLOW": "DB_DB_POOL_MAX_OVERFLOW",
        "DB_POOL_TIMEOUT": "DB_DB_POOL_TIMEOUT",
        "DB_POOL_RECYCLE": "DB_DB_POOL_RECYCLE",
        "DB_CONNECT_TIMEOUT": "DB_DB_CONNECT_TIMEOUT",
        "DB_QUERY_TIMEOUT": "DB_DB_QUERY_TIMEOUT",
    }

    for source_key, target_key in mapping.items():
        value = os.getenv(source_key)
        if value is None:
            continue
        os.environ.setdefault(target_key, value)
        os.environ.setdefault(target_key.lower(), value)

    db_type = os.getenv("DB_TYPE")
    if db_type is not None:
        os.environ.setdefault("db_type", db_type)


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
