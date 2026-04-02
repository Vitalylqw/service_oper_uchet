"""Shared runtime environment loader for config.env-based workflows."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = PROJECT_ROOT / "config.env"

_DOTENV_LOADED = False


def load_runtime_env(env_file: str | None = None) -> Path:
    """Load runtime environment once and promote legacy DB variables."""
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

    promote_legacy_database_env()
    _DOTENV_LOADED = True
    return env_path


def promote_legacy_database_env() -> None:
    """Map legacy `config.env` DB variables to `DatabaseConfig` names."""
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
