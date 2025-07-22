"""
Event Store implementation for Event Sourcing.

Manages domain events storage and retrieval with PostgreSQL JSONB.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.interfaces import EventStore
from .models import EventStoreModel


class EventStoreImplementation(EventStore):
    """
    PostgreSQL-based Event Store implementation.

    Stores domain events in JSONB format with efficient indexing.
    Supports event versioning and upcasting patterns.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize event store with database session."""
        self.session = session

    async def append_event(
        self,
        aggregate_id: uuid.UUID,
        event_type: str,
        event_data: dict[str, Any],
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Append single event to event store.

        Args:
            aggregate_id: ID of the aggregate that generated the event
            event_type: Type of the event (e.g., 'DealCreated', 'DealUpdated')
            event_data: Event payload data
            metadata: Optional metadata (user_id, correlation_id, etc.)

        Raises:
            Exception: If event cannot be stored
        """
        try:
            # Generate sequence number
            sequence_number = await self._get_next_sequence_number(aggregate_id)

            # Determine aggregate type from event type
            aggregate_type = self._extract_aggregate_type(event_type)

            # Create event record
            event_record = EventStoreModel(
                event_id=uuid.uuid4(),
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                event_type=event_type,
                event_version=1,  # Current event schema version
                event_data=event_data,
                event_metadata=metadata or {},
                sequence_number=sequence_number,
                created_at=datetime.now()
            )

            self.session.add(event_record)
            await self.session.flush()

            logger.debug(
                f"Event appended: {event_type} for aggregate {aggregate_id} "
                f"(sequence: {sequence_number})"
            )

        except Exception as e:
            logger.error(f"Failed to append event {event_type} for aggregate {aggregate_id}: {e}")
            raise

    async def append_events(self, events: list[dict[str, Any]]) -> None:
        """
        Append multiple events in batch for better performance.

        Args:
            events: List of event dictionaries with required fields:
                   - aggregate_id: UUID
                   - event_type: str
                   - event_data: dict
                   - metadata: dict (optional)

        Raises:
            Exception: If any event cannot be stored
        """
        if not events:
            return

        try:
            event_records = []

            for event in events:
                aggregate_id = event["aggregate_id"]
                sequence_number = await self._get_next_sequence_number(aggregate_id)
                aggregate_type = self._extract_aggregate_type(event["event_type"])

                event_record = EventStoreModel(
                    event_id=uuid.uuid4(),
                    aggregate_id=aggregate_id,
                    aggregate_type=aggregate_type,
                    event_type=event["event_type"],
                    event_version=1,
                    event_data=event["event_data"],
                    event_metadata=event.get("metadata", {}),
                    sequence_number=sequence_number,
                    created_at=datetime.now()
                )
                event_records.append(event_record)

            self.session.add_all(event_records)
            await self.session.flush()

            logger.info(f"Batch appended {len(events)} events")

        except Exception as e:
            logger.error(f"Failed to append batch of {len(events)} events: {e}")
            raise

    async def get_events(
        self,
        aggregate_id: uuid.UUID,
        from_version: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get events for specific aggregate.

        Args:
            aggregate_id: ID of the aggregate
            from_version: Minimum sequence number to retrieve

        Returns:
            List of events ordered by sequence number
        """
        try:
            query = (
                select(EventStoreModel)
                .where(EventStoreModel.aggregate_id == aggregate_id)
                .where(EventStoreModel.sequence_number >= from_version)
                .order_by(EventStoreModel.sequence_number.asc())
            )

            result = await self.session.execute(query)
            event_models = result.scalars().all()

            events = []
            for event_model in event_models:
                event_dict = {
                    "event_id": event_model.event_id,
                    "aggregate_id": event_model.aggregate_id,
                    "aggregate_type": event_model.aggregate_type,
                    "event_type": event_model.event_type,
                    "event_version": event_model.event_version,
                    "event_data": await self._upcast_event_data(
                        event_model.event_data,
                        event_model.event_type,
                        event_model.event_version
                    ),
                    "metadata": event_model.event_metadata,
                    "sequence_number": event_model.sequence_number,
                    "created_at": event_model.created_at,
                }
                events.append(event_dict)

            logger.debug(f"Retrieved {len(events)} events for aggregate {aggregate_id}")
            return events

        except Exception as e:
            logger.error(f"Failed to get events for aggregate {aggregate_id}: {e}")
            raise

    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get events by type with pagination.

        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return

        Returns:
            List of events ordered by creation time (newest first)
        """
        try:
            query = (
                select(EventStoreModel)
                .where(EventStoreModel.event_type == event_type)
                .order_by(desc(EventStoreModel.created_at))
                .limit(limit)
            )

            result = await self.session.execute(query)
            event_models = result.scalars().all()

            events = []
            for event_model in event_models:
                event_dict = {
                    "event_id": event_model.event_id,
                    "aggregate_id": event_model.aggregate_id,
                    "aggregate_type": event_model.aggregate_type,
                    "event_type": event_model.event_type,
                    "event_version": event_model.event_version,
                    "event_data": await self._upcast_event_data(
                        event_model.event_data,
                        event_model.event_type,
                        event_model.event_version
                    ),
                    "metadata": event_model.event_metadata,
                    "sequence_number": event_model.sequence_number,
                    "created_at": event_model.created_at,
                }
                events.append(event_dict)

            logger.debug(f"Retrieved {len(events)} events of type {event_type}")
            return events

        except Exception as e:
            logger.error(f"Failed to get events by type {event_type}: {e}")
            raise

    async def get_latest_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get latest events across all aggregates.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of latest events ordered by creation time (newest first)
        """
        try:
            query = (
                select(EventStoreModel)
                .order_by(desc(EventStoreModel.created_at))
                .limit(limit)
            )

            result = await self.session.execute(query)
            event_models = result.scalars().all()

            events = []
            for event_model in event_models:
                event_dict = {
                    "event_id": event_model.event_id,
                    "aggregate_id": event_model.aggregate_id,
                    "aggregate_type": event_model.aggregate_type,
                    "event_type": event_model.event_type,
                    "event_version": event_model.event_version,
                    "event_data": await self._upcast_event_data(
                        event_model.event_data,
                        event_model.event_type,
                        event_model.event_version
                    ),
                    "metadata": event_model.event_metadata,
                    "sequence_number": event_model.sequence_number,
                    "created_at": event_model.created_at,
                }
                events.append(event_dict)

            logger.debug(f"Retrieved {len(events)} latest events")
            return events

        except Exception as e:
            logger.error(f"Failed to get latest events: {e}")
            raise

    async def _get_next_sequence_number(self, aggregate_id: uuid.UUID) -> int:
        """Get next sequence number for aggregate."""
        try:
            query = (
                select(func.max(EventStoreModel.sequence_number))
                .where(EventStoreModel.aggregate_id == aggregate_id)
            )

            result = await self.session.execute(query)
            max_sequence = result.scalar()

            return (max_sequence or 0) + 1

        except Exception as e:
            logger.error(f"Failed to get next sequence number for aggregate {aggregate_id}: {e}")
            raise

    def _extract_aggregate_type(self, event_type: str) -> str:
        """
        Extract aggregate type from event type.

        Examples:
            'DealCreated' -> 'Deal'
            'DealItemAdded' -> 'Deal'
            'SyncSessionStarted' -> 'SyncSession'
        """
        if event_type.startswith("Deal"):
            return "Deal"
        elif event_type.startswith("SyncSession"):
            return "SyncSession"
        else:
            # Fallback: extract from event name
            return event_type.split("Created")[0].split("Updated")[0].split("Deleted")[0]

    async def _upcast_event_data(
        self,
        event_data: dict[str, Any],
        event_type: str,
        event_version: int
    ) -> dict[str, Any]:
        """
        Upcast event data to current version (Upcaster Pattern).

        This allows for event schema evolution while maintaining backward compatibility.
        Currently returns data as-is since we're starting with version 1.

        Args:
            event_data: Raw event data from database
            event_type: Type of the event
            event_version: Version of the event schema

        Returns:
            Upcasted event data compatible with current code
        """
        # For now, return data as-is since we're starting with version 1
        # In the future, add version-specific transformations here
        if event_version == 1:
            return event_data

        # Example of future upcasting:
        # if event_type == "DealCreated" and event_version == 1:
        #     # Upcast from v1 to v2 (add new fields, rename fields, etc.)
        #     return self._upcast_deal_created_v1_to_v2(event_data)

        logger.warning(f"Unknown event version {event_version} for type {event_type}")
        return event_data

    async def get_event_count(self) -> int:
        """Get total number of events in store."""
        try:
            query = select(func.count(EventStoreModel.id))
            result = await self.session.execute(query)
            count = result.scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            return 0

    async def get_aggregate_version(self, aggregate_id: uuid.UUID) -> int:
        """Get current version (highest sequence number) for aggregate."""
        try:
            query = (
                select(func.max(EventStoreModel.sequence_number))
                .where(EventStoreModel.aggregate_id == aggregate_id)
            )

            result = await self.session.execute(query)
            version = result.scalar()
            return version or 0

        except Exception as e:
            logger.error(f"Failed to get aggregate version for {aggregate_id}: {e}")
            return 0
