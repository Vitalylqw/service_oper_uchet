"""
QA Suite Settings.

Centralized configuration for database connection, paths, and test parameters.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """QA Suite configuration settings."""

    # Database settings
    db_type: str = Field(default="postgresql", description="Database type")
    db_host: str = Field(default="so_pg", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="so_uchet", description="Database name")
    db_user: str = Field(default="so_user", description="Database user")
    db_password: str = Field(default="so_pass", description="Database password")

    # Paths
    qa_suite_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent,
        description="QA Suite root directory",
    )
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Project root directory",
    )
    reports_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "reports",
        description="Reports output directory",
    )
    fixtures_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "tests" / "fixtures",
        description="Test fixtures directory",
    )
    scenarios_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "tests" / "scenarios",
        description="Test scenarios directory",
    )
    temp_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "temp",
        description="Temporary files directory",
    )

    # Test execution settings
    continue_on_error: bool = Field(
        default=True, description="Continue running tests after failure"
    )
    verbose_logging: bool = Field(default=True, description="Enable verbose logging")
    cleanup_temp_files: bool = Field(
        default=True, description="Clean up temporary files after tests"
    )
    create_events: bool = Field(default=True, description="Create events during sync")
    update_read_models: bool = Field(
        default=True, description="Update read models during sync"
    )

    # Timeouts
    sync_timeout_seconds: int = Field(default=300, description="Sync operation timeout")
    db_query_timeout_seconds: int = Field(default=60, description="DB query timeout")

    class Config:
        env_prefix = "QA_SUITE_"
        env_file = ".env"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database connection URL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings


def load_env_from_config() -> None:
    """Load environment variables from project config.env file."""
    config_file = Path(__file__).parent.parent.parent / "config.env"

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)
                    os.environ.setdefault(key.lower(), value)
