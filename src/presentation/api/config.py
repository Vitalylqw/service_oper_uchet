"""
API configuration.

Contains settings and configuration for FastAPI application.
"""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    """API configuration settings."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"  # Allow extra fields from env files
    )

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production-please", description="JWT secret key"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=15, description="Access token expiration (minutes)"
    )
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration (days)")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/dbname",
        description="Database connection URL",
    )

    # Environment
    environment: Literal["development", "testing", "production"] = Field(
        default="development", description="Environment"
    )

    # Database settings (optional, can be in extra fields)
    db_type: str = Field(default="sqlite", description="Database type")
    db_sqlite_db_path: str = Field(default="data/service_oper_uchet.sqlite", description="SQLite path")

    # File system paths
    excel_source_path: str = Field(default="data/excel/", description="Excel source path")
    excel_backup_path: str = Field(default="data/backup/", description="Excel backup path")
    excel_downloads_path: str = Field(default="data/downloads/", description="Excel downloads path")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Health checks
    health_check_timeout: int = Field(default=5, description="Health check timeout seconds")


# Global config instance
config = APIConfig()
