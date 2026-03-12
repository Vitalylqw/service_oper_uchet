"""
Repository interfaces for domain layer.

Contains abstract repository interfaces following Repository pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from ..models import Deal, SyncSession


class DealRepository(ABC):
    """Abstract repository for Deal entities."""

    @abstractmethod
    async def get_by_id(self, deal_id: UUID) -> Deal | None:
        """Get deal by ID."""
        pass

    @abstractmethod
    async def get_by_key(self, deal_key: str) -> Deal | None:
        """Get deal by business key."""
        pass

    @abstractmethod
    async def find_by_client(self, client_name: str) -> list[Deal]:
        """Find deals by client name."""
        pass

    @abstractmethod
    async def find_by_period(self, period_month: str, period_year: str) -> list[Deal]:
        """Find deals by period."""
        pass

    @abstractmethod
    async def save(self, deal: Deal) -> None:
        """Save deal to repository."""
        pass

    @abstractmethod
    async def save_batch(self, deals: list[Deal]) -> None:
        """Save multiple deals in batch."""
        pass

    @abstractmethod
    async def delete(self, deal_id: UUID) -> None:
        """Delete deal from repository."""
        pass

    @abstractmethod
    async def get_all_keys(self) -> list[str]:
        """Get all deal keys for change detection."""
        pass


class SyncSessionRepository(ABC):
    """Abstract repository for SyncSession entities."""

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> SyncSession | None:
        """Get sync session by ID."""
        pass

    @abstractmethod
    async def get_running_session(self) -> SyncSession | None:
        """Get currently running sync session."""
        pass

    @abstractmethod
    async def get_latest_sessions(self, limit: int = 10) -> list[SyncSession]:
        """Get latest sync sessions."""
        pass

    @abstractmethod
    async def save(self, session: SyncSession) -> None:
        """Save sync session to repository."""
        pass

    @abstractmethod
    async def find_by_status(self, status: str) -> list[SyncSession]:
        """Find sync sessions by status."""
        pass

    @abstractmethod
    async def find_by_period(self, start_date: str, end_date: str) -> list[SyncSession]:
        """Find sync sessions by date period."""
        pass


class EventStore(ABC):
    """Abstract event store for Event Sourcing."""

    @abstractmethod
    async def append_event(
        self,
        aggregate_id: UUID,
        event_type: str,
        event_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append event to event store."""
        pass

    @abstractmethod
    async def append_events(self, events: list[dict[str, Any]]) -> None:
        """Append multiple events in batch."""
        pass

    @abstractmethod
    async def get_events(self, aggregate_id: UUID, from_version: int = 0) -> list[dict[str, Any]]:
        """Get events for aggregate."""
        pass

    @abstractmethod
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get events by type."""
        pass

    @abstractmethod
    async def get_latest_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get latest events."""
        pass


class ReadModelRepository(ABC):
    """Abstract repository for read models (CQRS)."""

    @abstractmethod
    async def rebuild_deal_read_model(self) -> None:
        """Rebuild deal read model from events."""
        pass

    @abstractmethod
    async def rebuild_position_read_model(self) -> None:
        """Rebuild position read model from events."""
        pass

    @abstractmethod
    async def rebuild_stats_read_model(self) -> None:
        """Rebuild stats read model from events."""
        pass

    @abstractmethod
    async def get_deal_stats(
        self, period_month: str | None = None, period_year: str | None = None
    ) -> dict[str, Any]:
        """Get deal statistics from read model."""
        pass

    @abstractmethod
    async def get_position_stats(self, supplier_name: str | None = None) -> dict[str, Any]:
        """Get position statistics from read model."""
        pass

    @abstractmethod
    async def search_deals(
        self, query: str, filters: dict[str, Any] | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Search deals with filters and pagination."""
        pass
