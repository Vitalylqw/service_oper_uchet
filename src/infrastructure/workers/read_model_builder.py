"""
Read Model Builder Worker.

Updates read models based on domain events from Event Store.
Implements CQRS pattern by maintaining denormalized views for queries.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.interfaces import EventStore
from ...domain.models import Deal, DealItem
from ..database.models import (
    ReadModelAudit,
    ReadModelDeal,
    ReadModelPosition,
    ReadModelStats,
)


class ReadModelBuilder:
    """
    Worker for building and updating read models from domain events.

    Processes events from Event Store and updates corresponding read models
    for efficient querying in CQRS architecture.
    """

    def __init__(self, session: AsyncSession, event_store: EventStore) -> None:
        """Initialize read model builder with dependencies."""
        self.session = session
        self.event_store = event_store

    async def process_latest_events(self, limit: int = 100) -> int:
        """
        Process latest events from Event Store and update read models.

        Args:
            limit: Maximum number of events to process in one batch

        Returns:
            Number of events processed
        """
        try:
            # Get latest unprocessed events
            events = await self.event_store.get_latest_events(limit=limit)

            if not events:
                logger.debug("No new events to process")
                return 0

            processed_count = 0

            for event in events:
                await self._process_single_event(event)
                processed_count += 1

            await self.session.commit()
            logger.info(f"Successfully processed {processed_count} events")

            return processed_count

        except Exception as e:
            logger.error(f"Failed to process events: {e}")
            await self.session.rollback()
            raise

    async def process_events_by_type(self, event_type: str, limit: int = 100) -> int:
        """
        Process specific type of events.

        Args:
            event_type: Type of events to process
            limit: Maximum number of events to process

        Returns:
            Number of events processed
        """
        try:
            events = await self.event_store.get_events_by_type(
                event_type=event_type,
                limit=limit
            )

            processed_count = 0

            for event in events:
                await self._process_single_event(event)
                processed_count += 1

            await self.session.commit()
            logger.info(f"Processed {processed_count} events of type {event_type}")

            return processed_count

        except Exception as e:
            logger.error(f"Failed to process {event_type} events: {e}")
            await self.session.rollback()
            raise

    async def rebuild_read_model(self, aggregate_id: uuid.UUID) -> None:
        """
        Rebuild read model for specific aggregate from all its events.

        Args:
            aggregate_id: ID of aggregate to rebuild
        """
        try:
            # Get all events for this aggregate
            events = await self.event_store.get_events(aggregate_id=aggregate_id)

            if not events:
                logger.warning(f"No events found for aggregate {aggregate_id}")
                return

            # Clear existing read models for this aggregate
            await self._clear_read_models_for_aggregate(aggregate_id)

            # Replay all events
            for event in events:
                await self._process_single_event(event)

            await self.session.commit()
            logger.info(f"Rebuilt read model for aggregate {aggregate_id}")

        except Exception as e:
            logger.error(f"Failed to rebuild read model for {aggregate_id}: {e}")
            await self.session.rollback()
            raise

    async def _process_single_event(self, event: dict[str, Any]) -> None:
        """
        Process single event and update appropriate read models.

        Args:
            event: Event data from Event Store
        """
        event_type = event["event_type"]
        event_data = event["event_data"]
        aggregate_id = event["aggregate_id"]

        logger.debug(f"Processing event {event_type} for aggregate {aggregate_id}")

        # Route event to appropriate handler (check specific types first)
        if event_type.startswith("DealItem"):
            await self._handle_deal_item_event(event_type, event_data, event)
        elif event_type.startswith("Deal"):
            await self._handle_deal_event(event_type, event_data, event)
        elif event_type.startswith("Sync"):
            await self._handle_sync_event(event_type, event_data, event)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    async def _handle_deal_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Handle Deal-related events."""
        if event_type == "DealCreated":
            await self._create_deal_read_model(event_data, full_event)
        elif event_type == "DealUpdated":
            await self._update_deal_read_model(event_data, full_event)
        elif event_type == "DealDeleted":
            await self._delete_deal_read_model(event_data, full_event)
        else:
            logger.warning(f"Unknown deal event type: {event_type}")

    async def _handle_deal_item_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Handle DealItem-related events."""
        if event_type == "DealItemCreated":
            await self._create_deal_item_read_model(event_data, full_event)
        elif event_type == "DealItemUpdated":
            await self._update_deal_item_read_model(event_data, full_event)
        elif event_type == "DealItemDeleted":
            await self._delete_deal_item_read_model(event_data, full_event)
        else:
            logger.warning(f"Unknown deal item event type: {event_type}")

    async def _handle_sync_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Handle Sync-related events."""
        if event_type == "SyncSessionStarted":
            logger.debug("Sync session started - no read model updates needed")
        elif event_type == "SyncSessionCompleted":
            await self._update_stats_after_sync(event_data, full_event)
        else:
            logger.warning(f"Unknown sync event type: {event_type}")

    async def _create_deal_read_model(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Create read model entry for new deal."""
        try:
            # Parse deal data from event
            deal_data = event_data.get("deal", {})
            deal = Deal.model_validate(deal_data)

            # Create read model entry
            read_deal = ReadModelDeal(
                id=deal.id,
                deal_key=deal.deal_key,
                hash_key=str(deal.hash_key),

                # Basic info
                client_name=deal.client_name,
                invoice_info=deal.invoice_info,
                invoice_number=deal.invoice_number,
                invoice_date=deal.invoice_date,

                # Period
                period_month=deal.period.month,
                period_year=deal.period.year,
                period_full_name=str(deal.period),

                # Status
                is_shipped=str(deal.is_shipped) if deal.is_shipped else None,
                is_paid=str(deal.is_paid) if deal.is_paid else None,

                # Documents
                upd_number=deal.upd_number,
                seller=deal.seller,

                # Financial data
                total_revenue_amount=deal.total_revenue.amount if deal.total_revenue else None,
                total_revenue_currency=deal.total_revenue.currency if deal.total_revenue else "RUB",

                total_margin_amount=deal.total_margin.amount if deal.total_margin else None,
                total_margin_currency=deal.total_margin.currency if deal.total_margin else "RUB",

                total_cost_amount=deal.total_cost.amount if deal.total_cost else None,
                total_cost_currency=deal.total_cost.currency if deal.total_cost else "RUB",

                kickback_amount_value=deal.kickback_amount.amount if deal.kickback_amount else None,
                kickback_amount_currency=deal.kickback_amount.currency if deal.kickback_amount else "RUB",

                # Aggregated fields
                items_count=len(deal.items),
                total_quantity=sum(item.quantity or 0 for item in deal.items),
            )

            # Use upsert to handle conflicts
            stmt = insert(ReadModelDeal).values(**read_deal.__dict__)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=stmt.excluded
            )

            await self.session.execute(stmt)

            # Create audit entry
            await self._create_audit_entry(
                entity_type="deal",
                entity_id=deal.id,
                entity_key=deal.deal_key,
                change_type="INSERT",
                event_id=full_event["event_id"],
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id")
            )

            logger.debug(f"Created read model for deal {deal.deal_key}")

        except Exception as e:
            logger.error(f"Failed to create deal read model: {e}")
            raise

    async def _update_deal_read_model(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Update existing deal read model."""
        try:
            deal_data = event_data.get("deal", {})
            deal = Deal.model_validate(deal_data)

            # Get changes from event
            changes = event_data.get("changes", {})

            # Update read model
            update_data = {
                "hash_key": str(deal.hash_key),
                "client_name": deal.client_name,
                "invoice_info": deal.invoice_info,
                "invoice_number": deal.invoice_number,
                "invoice_date": deal.invoice_date,
                "period_month": deal.period.month,
                "period_year": deal.period.year,
                "period_full_name": str(deal.period),
                "is_shipped": str(deal.is_shipped) if deal.is_shipped else None,
                "is_paid": str(deal.is_paid) if deal.is_paid else None,
                "upd_number": deal.upd_number,
                "seller": deal.seller,
                "total_revenue_amount": deal.total_revenue.amount if deal.total_revenue else None,
                "total_margin_amount": deal.total_margin.amount if deal.total_margin else None,
                "total_cost_amount": deal.total_cost.amount if deal.total_cost else None,
                "kickback_amount_value": deal.kickback_amount.amount if deal.kickback_amount else None,
                "items_count": len(deal.items),
                "total_quantity": sum(item.quantity or 0 for item in deal.items),
                "version": ReadModelDeal.version + 1
            }

            stmt = (
                update(ReadModelDeal)
                .where(ReadModelDeal.id == deal.id)
                .values(**update_data)
            )

            await self.session.execute(stmt)

            # Create audit entries for each changed field
            for field_name, change_data in changes.items():
                await self._create_audit_entry(
                    entity_type="deal",
                    entity_id=deal.id,
                    entity_key=deal.deal_key,
                    change_type="UPDATE",
                    field_name=field_name,
                    old_value=str(change_data.get("old_value")),
                    new_value=str(change_data.get("new_value")),
                    event_id=full_event["event_id"],
                    sync_session_id=full_event.get("metadata", {}).get("sync_session_id")
                )

            logger.debug(f"Updated read model for deal {deal.deal_key}")

        except Exception as e:
            logger.error(f"Failed to update deal read model: {e}")
            raise

    async def _delete_deal_read_model(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Soft delete deal read model."""
        try:
            deal_id = uuid.UUID(event_data.get("deal_id"))
            deal_key = event_data.get("deal_key", "")

            # Soft delete - set is_active = False
            stmt = (
                update(ReadModelDeal)
                .where(ReadModelDeal.id == deal_id)
                .values(is_active=False, version=ReadModelDeal.version + 1)
            )

            await self.session.execute(stmt)

            # Also soft delete related positions
            position_stmt = (
                update(ReadModelPosition)
                .where(ReadModelPosition.deal_id == deal_id)
                .values(is_active=False, version=ReadModelPosition.version + 1)
            )

            await self.session.execute(position_stmt)

            # Create audit entry
            await self._create_audit_entry(
                entity_type="deal",
                entity_id=deal_id,
                entity_key=deal_key,
                change_type="DELETE",
                event_id=full_event["event_id"],
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id")
            )

            logger.debug(f"Deleted read model for deal {deal_key}")

        except Exception as e:
            logger.error(f"Failed to delete deal read model: {e}")
            raise

    async def _create_deal_item_read_model(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Create read model entry for new deal item."""
        try:
            item_data = event_data.get("deal_item", {})
            item = DealItem.model_validate(item_data)

            # Get deal context for denormalization
            deal_context = await self._get_deal_context(item.deal_id)

            read_position = ReadModelPosition(
                id=item.id,
                deal_id=item.deal_id,
                deal_key=deal_context.get("deal_key", ""),

                # Item info
                position_key=item.item_key,
                hash_key=str(item.hash_key),
                product_name=item.product_name,
                supplier_name=item.supplier_name,
                pickup_date=item.pickup_date,

                # Quantities and pricing
                quantity=item.quantity,
                purchase_price_amount=item.purchase_price.amount if item.purchase_price else None,
                purchase_price_currency=item.purchase_price.currency if item.purchase_price else "RUB",
                sale_price_amount=item.sale_price.amount if item.sale_price else None,
                sale_price_currency=item.sale_price.currency if item.sale_price else "RUB",
                revenue_amount=item.revenue.amount if item.revenue else None,
                revenue_currency=item.revenue.currency if item.revenue else "RUB",
                margin_amount=item.margin.amount if item.margin else None,
                margin_currency=item.margin.currency if item.margin else "RUB",
                cost_amount=item.cost.amount if item.cost else None,
                cost_currency=item.cost.currency if item.cost else "RUB",

                # Deal context (denormalized)
                client_name=deal_context.get("client_name", ""),
                period_month=deal_context.get("period_month", ""),
                period_year=deal_context.get("period_year", ""),
            )

            # Use upsert to handle conflicts
            stmt = insert(ReadModelPosition).values(**read_position.__dict__)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=stmt.excluded
            )

            await self.session.execute(stmt)

            # Create audit entry
            await self._create_audit_entry(
                entity_type="position",
                entity_id=item.id,
                entity_key=item.item_key,
                change_type="INSERT",
                event_id=full_event["event_id"],
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id")
            )

            logger.debug(f"Created read model for position {item.item_key}")

        except Exception as e:
            logger.error(f"Failed to create deal item read model: {e}")
            raise

    async def _update_deal_item_read_model(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Update existing deal item read model."""
        try:
            item_data = event_data.get("deal_item", {})
            item = DealItem.model_validate(item_data)

            # Get changes from event
            changes = event_data.get("changes", {})

            # Get deal context for denormalization
            deal_context = await self._get_deal_context(item.deal_id)

            # Update read model
            update_data = {
                "hash_key": str(item.hash_key),
                "product_name": item.product_name,
                "supplier_name": item.supplier_name,
                "pickup_date": item.pickup_date,
                "quantity": item.quantity,
                "purchase_price_amount": item.purchase_price.amount if item.purchase_price else None,
                "purchase_price_currency": item.purchase_price.currency if item.purchase_price else "RUB",
                "sale_price_amount": item.sale_price.amount if item.sale_price else None,
                "sale_price_currency": item.sale_price.currency if item.sale_price else "RUB",
                "revenue_amount": item.revenue.amount if item.revenue else None,
                "revenue_currency": item.revenue.currency if item.revenue else "RUB",
                "margin_amount": item.margin.amount if item.margin else None,
                "margin_currency": item.margin.currency if item.margin else "RUB",
                "cost_amount": item.cost.amount if item.cost else None,
                "cost_currency": item.cost.currency if item.cost else "RUB",
                # Update denormalized deal context
                "client_name": deal_context.get("client_name", ""),
                "period_month": deal_context.get("period_month", ""),
                "period_year": deal_context.get("period_year", ""),
                "version": ReadModelPosition.version + 1
            }

            stmt = (
                update(ReadModelPosition)
                .where(ReadModelPosition.id == item.id)
                .values(**update_data)
            )

            await self.session.execute(stmt)

            # Create audit entries for each changed field
            for field_name, change_data in changes.items():
                await self._create_audit_entry(
                    entity_type="position",
                    entity_id=item.id,
                    entity_key=item.item_key,
                    change_type="UPDATE",
                    field_name=field_name,
                    old_value=str(change_data.get("old_value")),
                    new_value=str(change_data.get("new_value")),
                    event_id=full_event["event_id"],
                    sync_session_id=full_event.get("metadata", {}).get("sync_session_id")
                )

            logger.debug(f"Updated read model for position {item.item_key}")

        except Exception as e:
            logger.error(f"Failed to update deal item read model: {e}")
            raise

    async def _delete_deal_item_read_model(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Soft delete deal item read model."""
        try:
            item_id = uuid.UUID(event_data.get("deal_item_id"))
            item_key = event_data.get("item_key", "")

            # Soft delete - set is_active = False
            stmt = (
                update(ReadModelPosition)
                .where(ReadModelPosition.id == item_id)
                .values(is_active=False, version=ReadModelPosition.version + 1)
            )

            await self.session.execute(stmt)

            # Create audit entry
            await self._create_audit_entry(
                entity_type="position",
                entity_id=item_id,
                entity_key=item_key,
                change_type="DELETE",
                event_id=full_event["event_id"],
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id")
            )

            logger.debug(f"Deleted read model for position {item_key}")

        except Exception as e:
            logger.error(f"Failed to delete deal item read model: {e}")
            raise

    async def _update_stats_after_sync(
        self,
        event_data: dict[str, Any],
        full_event: dict[str, Any]
    ) -> None:
        """Update statistics after sync completion."""
        try:
            sync_session_data = event_data.get("sync_session", {})
            sync_type = sync_session_data.get("sync_type", "unknown")
            stats = event_data.get("stats", {})

            # Extract sync date for grouping
            from datetime import datetime
            sync_date = datetime.now().strftime("%Y-%m")  # YYYY-MM format

            # Calculate key metrics from stats
            total_deals = stats.get("total_processed", 0)
            stats.get("new_deals", 0)
            stats.get("updated_deals", 0)
            stats.get("deleted_deals", 0)

            total_positions = stats.get("total_positions", 0)

            # Calculate financial aggregates (if available)
            total_revenue = stats.get("total_revenue", 0)
            total_margin = stats.get("total_margin", 0)
            total_cost = stats.get("total_cost", 0)
            total_quantity = stats.get("total_quantity", 0)

            # Insert or update daily stats
            daily_stats = ReadModelStats(
                stat_type="daily",
                stat_date=sync_date,
                dimension_type="sync_type",
                dimension_value=sync_type,
                deals_count=total_deals,
                positions_count=total_positions,
                total_revenue=Decimal(str(total_revenue)),
                total_margin=Decimal(str(total_margin)),
                total_cost=Decimal(str(total_cost)),
                total_quantity=Decimal(str(total_quantity)),
                shipped_deals_count=stats.get("shipped_deals", 0),
                paid_deals_count=stats.get("paid_deals", 0)
            )

            # Use upsert to handle conflicts
            from sqlalchemy.dialects.postgresql import insert
            stmt = insert(ReadModelStats).values(**daily_stats.__dict__)
            stmt = stmt.on_conflict_do_update(
                index_elements=['stat_type', 'stat_date', 'dimension_type', 'dimension_value'],
                set_={
                    'deals_count': stmt.excluded.deals_count,
                    'positions_count': stmt.excluded.positions_count,
                    'total_revenue': stmt.excluded.total_revenue,
                    'total_margin': stmt.excluded.total_margin,
                    'total_cost': stmt.excluded.total_cost,
                    'total_quantity': stmt.excluded.total_quantity,
                    'shipped_deals_count': stmt.excluded.shipped_deals_count,
                    'paid_deals_count': stmt.excluded.paid_deals_count,
                    'calculated_at': func.now()
                }
            )

            await self.session.execute(stmt)

            logger.info(f"Updated statistics for sync session: {sync_type} on {sync_date}")

        except Exception as e:
            logger.error(f"Failed to update stats after sync: {e}")
            raise

    async def _get_deal_context(self, deal_id: uuid.UUID | None) -> dict[str, Any]:
        """Get deal context for denormalizing position data."""
        if not deal_id:
            return {}

        try:
            query = select(ReadModelDeal).where(ReadModelDeal.id == deal_id)
            result = await self.session.execute(query)
            deal = result.scalar_one_or_none()

            if deal:
                return {
                    "deal_key": deal.deal_key,
                    "client_name": deal.client_name,
                    "period_month": deal.period_month,
                    "period_year": deal.period_year,
                }
            return {}

        except Exception as e:
            logger.error(f"Failed to get deal context for {deal_id}: {e}")
            return {}

    async def _create_audit_entry(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_key: str,
        change_type: str,
        event_id: uuid.UUID,
        sync_session_id: uuid.UUID | None = None,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None
    ) -> None:
        """Create audit trail entry."""
        try:
            audit_entry = ReadModelAudit(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_key=entity_key,
                change_type=change_type,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                sync_session_id=sync_session_id or uuid.uuid4(),
                event_id=event_id
            )

            self.session.add(audit_entry)

        except Exception as e:
            logger.error(f"Failed to create audit entry: {e}")
            raise

    async def _clear_read_models_for_aggregate(self, aggregate_id: uuid.UUID) -> None:
        """Clear all read models for specific aggregate."""
        try:
            # Delete deal read model
            await self.session.execute(
                delete(ReadModelDeal).where(ReadModelDeal.id == aggregate_id)
            )

            # Delete related positions
            await self.session.execute(
                delete(ReadModelPosition).where(ReadModelPosition.deal_id == aggregate_id)
            )

            logger.debug(f"Cleared read models for aggregate {aggregate_id}")

        except Exception as e:
            logger.error(f"Failed to clear read models for {aggregate_id}: {e}")
            raise
