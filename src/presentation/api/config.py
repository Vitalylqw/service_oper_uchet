"""
API configuration.

Contains settings and configuration for FastAPI application.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    """API configuration settings."""

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production-please",
        description="JWT secret key"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=15, description="Access token expiration (minutes)")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration (days)")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/dbname",
        description="Database connection URL"
    )

    # Environment
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Environment"
    )

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
config = APIConfig()
