"""
Database Infrastructure Layer.

Contains:
- connection: Database connection management
- models: SQLAlchemy models for Event Store and Read Models
- repositories: Repository implementations
- migrations: Alembic migration scripts
- event_store: Event Sourcing implementation

Технологии: PostgreSQL 16, SQLAlchemy 2.0, asyncpg
"""

from .connection import DatabaseConfig, get_database_session
from .event_store import EventStoreImplementation
from .models import Base
from .repositories import DealRepositoryImplementation, SyncSessionRepositoryImplementation

__all__ = [
    "DatabaseConfig",
    "get_database_session",
    "EventStoreImplementation",
    "Base",
    "DealRepositoryImplementation",
    "SyncSessionRepositoryImplementation",
]
