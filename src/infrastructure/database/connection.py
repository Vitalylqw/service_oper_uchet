"""
Database connection management for PostgreSQL and SQLite.

Manages async connections with automatic database type detection and configuration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import ConfigDict, Field, computed_field
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker


class DatabaseConfig(BaseSettings):
    """Database configuration settings with SQLite and PostgreSQL support."""

    # Database type selection
    db_type: Literal["sqlite", "postgresql"] = Field(
        default="sqlite", description="Database type (sqlite for dev, postgresql for prod)"
    )

    # SQLite configuration (for development/testing)
    sqlite_db_path: str = Field(
        default="data/service_oper_uchet.sqlite",
        description="SQLite database file path"
    )

    # PostgreSQL connection parameters (for production)
    db_host: str = Field(default="192.168.31.5", description="PostgreSQL host")
    db_port: int = Field(default=5432, description="PostgreSQL port")
    db_name: str = Field(default="corp", description="PostgreSQL database name")
    db_user: str = Field(default="etl", description="PostgreSQL user")
    db_password: str = Field(default="", description="PostgreSQL password")

    # Connection pool settings (PostgreSQL only)
    db_pool_size: int = Field(default=10, description="Connection pool size")
    db_pool_max_overflow: int = Field(default=20, description="Pool max overflow")
    db_pool_timeout: int = Field(default=30, description="Pool timeout seconds")
    db_pool_recycle: int = Field(default=3600, description="Pool recycle seconds")

    # Connection timeouts
    db_connect_timeout: int = Field(default=10, description="Connect timeout seconds")
    db_query_timeout: int = Field(default=60, description="Query timeout seconds")

    # Event Store settings
    event_store_partition_months: int = Field(
        default=12, description="Event store partition months"
    )
    event_store_retention_months: int = Field(
        default=24, description="Event store retention months"
    )

    model_config = ConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")

    @computed_field
    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for migrations."""
        if self.db_type == "sqlite":
            # Ensure directory exists
            db_path = Path(self.sqlite_db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{self.sqlite_db_path}"
        else:
            return (
                f"postgresql://{self.db_user}:{self.db_password}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
            )

    @computed_field
    @property
    def async_database_url(self) -> str:
        """Asynchronous database URL for application."""
        if self.db_type == "sqlite":
            # Ensure directory exists
            db_path = Path(self.sqlite_db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{self.sqlite_db_path}"
        else:
            return (
                f"postgresql+asyncpg://{self.db_user}:{self.db_password}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
            )


class DatabaseManager:
    """Database connection manager with async session support."""

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize database manager."""
        self.config = config
        self._async_engine = None
        self._async_session_factory = None
        self._sync_engine = None
        self._sync_session_factory = None

    @property
    def async_engine(self):
        """Get or create async engine."""
        if self._async_engine is None:
            if self.config.db_type == "sqlite":
                # SQLite specific configuration
                self._async_engine = create_async_engine(
                    self.config.async_database_url,
                    echo=False,  # Set to True for SQL debug logging
                    future=True,
                    # SQLite doesn't support connection pooling like PostgreSQL
                    pool_pre_ping=True,
                    connect_args={"check_same_thread": False}  # For SQLite threading
                )
            else:
                # PostgreSQL configuration
                self._async_engine = create_async_engine(
                    self.config.async_database_url,
                    pool_size=self.config.db_pool_size,
                    max_overflow=self.config.db_pool_max_overflow,
                    pool_timeout=self.config.db_pool_timeout,
                    pool_recycle=self.config.db_pool_recycle,
                    echo=False,  # Set to True for SQL debug logging
                    future=True,
                )
        return self._async_engine

    @property
    def async_session_factory(self):
        """Get or create async session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )
        return self._async_session_factory

    @property
    def sync_engine(self):
        """Get or create sync engine for migrations."""
        if self._sync_engine is None:
            if self.config.db_type == "sqlite":
                # SQLite sync engine
                self._sync_engine = create_engine(
                    self.config.sync_database_url,
                    echo=False,
                    future=True,
                    connect_args={"check_same_thread": False}
                )
            else:
                # PostgreSQL sync engine
                self._sync_engine = create_engine(
                    self.config.sync_database_url,
                    pool_size=self.config.db_pool_size,
                    max_overflow=self.config.db_pool_max_overflow,
                    pool_timeout=self.config.db_pool_timeout,
                    pool_recycle=self.config.db_pool_recycle,
                    echo=False,
                    future=True,
                )
        return self._sync_engine

    @property
    def sync_session_factory(self):
        """Get or create sync session factory."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                autoflush=True,
                autocommit=False,
            )
        return self._sync_session_factory

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with proper cleanup."""
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Database session error: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()

    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("✅ Database connection successful")
                return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    async def close(self) -> None:
        """Close all connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
_db_config = DatabaseConfig()
_db_manager = DatabaseManager(_db_config)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session in FastAPI.

    Usage in FastAPI:
        @app.get("/deals")
        async def get_deals(db: AsyncSession = Depends(get_database_session)):
            # Use db session
    """
    async with _db_manager.get_async_session() as session:
        yield session


async def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    return _db_manager


async def init_database() -> None:
    """Initialize database connection and test connectivity."""
    logger.info("Initializing database connection...")
    success = await _db_manager.test_connection()
    if not success:
        raise RuntimeError("Failed to initialize database connection")
    logger.info("Database initialization completed")


async def close_database() -> None:
    """Close database connections on shutdown."""
    logger.info("Closing database connections...")
    await _db_manager.close()
    logger.info("Database connections closed")


# For testing and development
async def reset_database_manager(config: DatabaseConfig | None = None) -> DatabaseManager:
    """Reset database manager with new config (for testing)."""
    global _db_manager, _db_config

    if config:
        _db_config = config

    await _db_manager.close()
    _db_manager = DatabaseManager(_db_config)
    return _db_manager
