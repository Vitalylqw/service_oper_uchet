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

from domain.interfaces import EventStore
from domain.models import Deal, DealItem

from ..database.models import (
    ReadModelAudit,
    ReadModelDeal,
    ReadModelPosition,
    ReadModelStats,
)
from .read_model_position_sync import PositionSyncLogic
from .deferred_event_queue import DeferredEventQueue


class ReadModelBuilder:
    """
    Worker for building and updating read models from domain events.

    Processes events from Event Store and updates corresponding read models
    for efficient querying in CQRS architecture.
    
    Implements hybrid approach: primary processing with deferred event handling
    for events that cannot be processed immediately.
    """

    def __init__(self, session: AsyncSession, event_store: EventStore) -> None:
        """Initialize read model builder with dependencies."""
        self.session = session
        self.event_store = event_store
        
        # Helper for mapping Status enum to DB string values
        from domain.value_objects.common import Status
        self._status_map = {
            Status.PENDING: "pending",
            Status.PARTIAL: "partial",
            Status.COMPLETED: "completed",
            Status.PAID: "paid",
            Status.SHIPPED: "shipped",
            Status.CANCELLED: "cancelled",
            Status.FAILED: "failed",
        }
        self.deferred_queue = DeferredEventQueue(max_retries=3)
        
        # Position synchronization logic
        self.position_sync = PositionSyncLogic(session)

    def _status_to_db(self, status):
        """Convert Status enum or string/None to canonical DB string."""
        if status is None:
            return None
        from domain.value_objects.common import Status
        if isinstance(status, Status):
            return self._status_map.get(status, "pending")
        if isinstance(status, str):
            lower = status.lower().strip()
            if lower in self._status_map.values():
                return lower
            # fallback mapping for yes/da etc.
            if lower in ["да", "yes", "true"]:
                return "completed"
            return "pending"
        return "pending"

    async def process_latest_events(self, limit: int = 100, auto_commit: bool = True) -> int:
        """
        Process latest events from Event Store and update read models.

        Args:
            limit: Maximum number of events to process in one batch
            auto_commit: Whether to commit transaction automatically

        Returns:
            Number of events processed (main + deferred)
        """
        try:
            # 1. Process main events
            main_processed = await self._process_main_events(limit)
            
            # 2. Process deferred events
            deferred_processed = await self.deferred_queue.process_deferred_events(
                self._process_single_event
            )
            
            if auto_commit:
                await self.session.commit()
            
            total_processed = main_processed + deferred_processed
            
            # Log queue status
            queue_status = self.deferred_queue.get_queue_status()
            logger.info(
                f"Processed {main_processed} main events + {deferred_processed} deferred events "
                f"(queue size: {queue_status['queue_size']})"
            )
            
            return total_processed

        except Exception as e:
            logger.error(f"Failed to process events: {e}")
            if auto_commit:
                await self.session.rollback()
            raise

    async def _process_main_events(self, limit: int) -> int:
        """Process main events from Event Store."""
        # Get latest unprocessed events
        events = await self.event_store.get_latest_events(limit=limit)

        if not events:
            logger.debug("No new events to process")
            return 0

        processed_count = 0

        for event in events:
            try:
                await self._process_single_event(event)
                processed_count += 1
            except Exception as e:
                # If event processing fails, defer it
                reason = f"Processing failed: {str(e)}"
                await self.deferred_queue.add_event(event, reason)
                logger.warning(f"Event processing failed, deferred: {event.get('event_type')} - {e}")

        return processed_count

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
            events = await self.event_store.get_events_by_type(event_type=event_type, limit=limit)

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

        # Отмечаем событие как обработанное
        try:
            from datetime import datetime as _dt
            from sqlalchemy import update as _update
            from ..database.models import EventStoreModel as _ESM
            await self.session.execute(
                _update(_ESM).where(_ESM.event_id == event["event_id"]).values(processed_at=_dt.utcnow())
            )
        except Exception as _e:
            logger.error(f"Failed to mark event {event['event_id']} as processed: {_e}")

    async def _handle_deal_event(
        self, event_type: str, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Handle Deal-related events."""
        if event_type == "DealCreated":
            await self._create_deal_read_model(event_data, full_event)
        elif event_type == "DealWithPositionsCreated":
            # NEW CORRECT LOGIC: Handle deal synchronization with all positions
            await self._sync_deal_with_positions(event_data, full_event)
        elif event_type == "DealUpdated":
            await self._update_deal_read_model(event_data, full_event)
        elif event_type == "DealDeleted":
            await self._delete_deal_read_model(event_data, full_event)
        else:
            logger.warning(f"Unknown deal event type: {event_type}")

    async def _handle_deal_item_event(
        self, event_type: str, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Handle DealItem-related events."""
        if event_type == "DealItemAdded":
            await self._create_deal_item_read_model(event_data, full_event)
        elif event_type == "DealItemUpdated":
            await self._update_deal_item_read_model(event_data, full_event)
        elif event_type == "DealItemDeleted":
            await self._delete_deal_item_read_model(event_data, full_event)
        else:
            logger.warning(f"Unknown deal item event type: {event_type}")

    async def _handle_sync_event(
        self, event_type: str, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Handle Sync-related events."""
        if event_type == "SyncSessionStarted":
            logger.debug("Sync session started - no read model updates needed")
        elif event_type == "SyncSessionCompleted":
            await self._update_stats_after_sync(event_data, full_event)
        else:
            logger.warning(f"Unknown sync event type: {event_type}")

    async def _sync_deal_with_positions(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """
        Synchronize deal with all its positions using correct versioning logic.
        
        This is the NEW CORRECT implementation that replaces item-by-item processing.
        Uses deal-level synchronization with proper hash_key comparison.
        """
        try:
            # Extract deal and items data from event
            deal_data = event_data.get("deal", event_data)
            items_data = event_data.get("items", [])
            
            logger.info(f"🔄 Starting deal synchronization: {deal_data.get('deal_key', 'UNKNOWN')} with {len(items_data)} positions")
            
            # Create Deal object from event data
            deal = await self._create_deal_object_from_event(deal_data, items_data)
            
            # Create or update deal read model first
            await self._upsert_deal_read_model(deal, full_event)
            
            # Get deal context for position denormalization
            deal_context = {
                "deal_key": deal.deal_key,
                "client_name": deal.client_name,
                "period_month": deal.period.month,
                "period_year": deal.period.year,
            }
            
            # CORRECT LOGIC: Synchronize positions at deal level
            sync_session_id = full_event.get("metadata", {}).get("sync_session_id")
            sync_stats = await self.position_sync.sync_deal_positions(
                deal, deal_context, sync_session_id
            )
            
            # Recalculate totals for the deal
            await self._recalculate_totals(deal.id)
            
            # Create audit entry for deal synchronization
            await self._create_audit_entry(
                entity_type="deal_sync",
                entity_id=deal.id,
                entity_key=deal.deal_key,
                change_type="SYNC",
                event_id=full_event["event_id"],
                sync_session_id=sync_session_id,
                additional_data=sync_stats,
            )
            
            logger.info(f"✅ Deal synchronization completed: {deal.deal_key} - {sync_stats}")
            
        except Exception as e:
            logger.error(f"Failed to synchronize deal with positions: {e}")
            raise

    async def _create_deal_object_from_event(
        self, deal_data: dict[str, Any], items_data: list[dict[str, Any]]
    ) -> Deal:
        """Create Deal object from event data with all items."""
        from domain.models import Deal, DealItem
        from domain.value_objects import Period, Money, SignedMoney
        
        # Extract and create period
        period_data = deal_data.get("period", {})
        try:
            if isinstance(period_data, dict) and period_data.get("month") and period_data.get("year"):
                period = Period(
                    month=period_data["month"],
                    year=period_data["year"],
                    full_name=period_data.get("full_name", f"{period_data['month']} {period_data['year']}")
                )
            else:
                logger.warning(f"Invalid period data in event: {period_data}, using default")
                period = Period(month="Январь", year="2025", full_name="Январь 2025")
        except Exception as e:
            logger.warning(f"Failed to create period from data {period_data}: {e}, using default")
            period = Period(month="Январь", year="2025", full_name="Январь 2025")
        
        # Extract totals
        totals = deal_data.get("totals", {})
        total_revenue = Money(amount=Decimal(totals["revenue"])) if totals.get("revenue") else None
        total_margin = SignedMoney(amount=Decimal(totals["margin"])) if totals.get("margin") else None
        total_cost = Money(amount=Decimal(totals["cost"])) if totals.get("cost") else None
        kickback_amount = Money(amount=Decimal(totals["kickback"])) if totals.get("kickback") else None
        
        # Create Deal object
        deal = Deal(
            id=uuid.UUID(deal_data["deal_id"]),
            deal_key=deal_data["deal_key"],
            client_name=deal_data["client_name"],
            invoice_info=deal_data.get("invoice_info", ""),
            invoice_number=deal_data.get("invoice_number", ""),
            invoice_date=deal_data.get("invoice_date"),
            period=period,
            is_shipped=deal_data.get("is_shipped"),
            is_paid=deal_data.get("is_paid"),
            upd_number=deal_data.get("upd_number", ""),
            seller=deal_data.get("seller", ""),
            total_revenue=total_revenue,
            total_margin=total_margin,
            total_cost=total_cost,
            kickback_amount=kickback_amount,
            items=[],
        )
        
        # Add items to deal
        for item_data in items_data:
            item = await self._create_deal_item_from_data(item_data, deal.id)
            deal.items.append(item)
        
        return deal

    async def _create_deal_item_from_data(self, item_data: dict[str, Any], deal_id: uuid.UUID) -> DealItem:
        """Create DealItem object from event data."""
        from domain.models import DealItem
        from domain.value_objects import Money, SignedMoney
        
        # Extract prices
        prices = item_data.get("prices", {})
        purchase_price = Money(amount=Decimal(prices["purchase"])) if prices.get("purchase") else None
        sale_price = Money(amount=Decimal(prices["sale"])) if prices.get("sale") else None
        revenue = Money(amount=Decimal(prices["revenue"])) if prices.get("revenue") else None
        margin = SignedMoney(amount=Decimal(prices["margin"])) if prices.get("margin") else None
        cost = Money(amount=Decimal(prices["cost"])) if prices.get("cost") else None
        
        return DealItem(
            id=uuid.UUID(item_data["item_id"]),
            deal_id=deal_id,
            item_key=item_data.get("product_name", ""),
            product_name=item_data["product_name"],
            supplier_name=item_data.get("supplier_name", ""),
            pickup_date=item_data.get("pickup_date"),
            quantity=Decimal(item_data["quantity"]) if item_data.get("quantity") else None,
            purchase_price=purchase_price,
            sale_price=sale_price,
            revenue=revenue,
            margin=margin,
            cost=cost,
            position_number=item_data.get("position_number", 1),  # Add position_number from event data
        )

    async def _upsert_deal_read_model(self, deal: Deal, full_event: dict[str, Any]) -> None:
        """Create or update deal read model."""
        read_deal_data = {
            "id": deal.id,
            "deal_key": deal.deal_key,
            "hash_key": str(deal.hash_key),
            # Basic info
            "client_name": deal.client_name,
            "invoice_info": deal.invoice_info,
            "invoice_number": deal.invoice_number,
            "invoice_date": deal.invoice_date,
            # Period
            "period_month": deal.period.month,
            "period_year": deal.period.year,
            "period_full_name": str(deal.period),
            # Status
            "is_shipped": self._status_to_db(deal.is_shipped),
            "is_paid": self._status_to_db(deal.is_paid),
            # Documents
            "upd_number": deal.upd_number,
            "seller": deal.seller,
            # Financial data
            "total_revenue_amount": deal.total_revenue.amount if deal.total_revenue else None,
            "total_margin_amount": deal.total_margin.amount if deal.total_margin else None,
            "total_cost_amount": deal.total_cost.amount if deal.total_cost else None,
            "kickback_amount_value": deal.kickback_amount.amount if deal.kickback_amount else None,
            # Calculated totals (to be filled later)
            "calc_revenue_amount": 0,
            "calc_margin_amount": 0,
            "calc_cost_amount": 0,
            "revenue_mismatch": 0,
            "margin_mismatch": 0,
            "cost_mismatch": 0,
            "has_totals_error": False,
            # Aggregated fields
            "items_count": len(deal.items),
            "total_quantity": sum(item.quantity or 0 for item in deal.items),
        }
        
        # Use upsert to handle conflicts on deal_key
        stmt = insert(ReadModelDeal).values(**read_deal_data)
        stmt = stmt.on_conflict_do_update(index_elements=["deal_key"], set_=stmt.excluded)
        await self.session.execute(stmt)

    async def _create_deal_read_model(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Create read model entry for new deal."""
        try:
            # Handle both formats: event_data.deal and direct event_data
            deal_data = event_data.get("deal", event_data)
            
            # Create a Deal object from the event data
            from domain.models import Deal
            from domain.value_objects import Period, Money, SignedMoney
            
            # Extract period data
            period_data = deal_data.get("period", {})
            
            # HYBRID APPROACH: Use valid fallback values for periods
            try:
                if isinstance(period_data, dict) and period_data.get("month") and period_data.get("year"):
                    period = Period(
                        month=period_data["month"],
                        year=period_data["year"],
                        full_name=period_data.get("full_name", f"{period_data['month']} {period_data['year']}")
                    )
                else:
                    logger.warning(f"Invalid period data in event: {period_data}, using default")
                    period = Period(month="Январь", year="2025", full_name="Январь 2025")
            except Exception as e:
                logger.warning(f"Failed to create period from data {period_data}: {e}, using default")
                period = Period(month="Январь", year="2025", full_name="Январь 2025")
            
            # Extract totals data
            totals = deal_data.get("totals", {})
            
            revenue_data = totals.get("revenue")
            total_revenue = Money(amount=Decimal(revenue_data)) if revenue_data else None
            
            margin_data = totals.get("margin")
            total_margin = SignedMoney(amount=Decimal(margin_data)) if margin_data else None
            
            cost_data = totals.get("cost")
            total_cost = Money(amount=Decimal(cost_data)) if cost_data else None
            
            kickback_data = totals.get("kickback")
            kickback_amount = Money(amount=Decimal(kickback_data)) if kickback_data else None

            # Create Deal object
            deal = Deal(
                id=uuid.UUID(deal_data["deal_id"]),
                deal_key=deal_data["deal_key"],
                client_name=deal_data["client_name"],
                invoice_info=deal_data.get("invoice_info", ""),
                invoice_number=deal_data.get("invoice_number", ""),
                invoice_date=deal_data.get("invoice_date"),
                period=period,
                is_shipped=deal_data.get("is_shipped"),
                is_paid=deal_data.get("is_paid"),
                upd_number=deal_data.get("upd_number", ""),
                seller=deal_data.get("seller", ""),
                total_revenue=total_revenue,
                total_margin=total_margin,
                total_cost=total_cost,
                kickback_amount=kickback_amount,
                items=[],  # Items are handled separately
            )

            # Create read model entry
            read_deal_data = {
                "id": deal.id,
                "deal_key": deal.deal_key,
                "hash_key": str(deal.hash_key),
                # Basic info
                "client_name": deal.client_name,
                "invoice_info": deal.invoice_info,
                "invoice_number": deal.invoice_number,
                "invoice_date": deal.invoice_date,
                # Period
                "period_month": period.month,
                "period_year": period.year,
                "period_full_name": str(period),
                # Status
                "is_shipped": self._status_to_db(deal.is_shipped),
                "is_paid": self._status_to_db(deal.is_paid),
                # Documents
                "upd_number": deal.upd_number,
                "seller": deal.seller,
                # Financial data
                "total_revenue_amount": deal.total_revenue.amount if deal.total_revenue else None,
                "total_margin_amount": deal.total_margin.amount if deal.total_margin else None,
                "total_cost_amount": deal.total_cost.amount if deal.total_cost else None,
                "kickback_amount_value": deal.kickback_amount.amount if deal.kickback_amount else None,
                # Calculated totals (to be filled later)
                "calc_revenue_amount": 0,
                "calc_margin_amount": 0,
                "calc_cost_amount": 0,
                "revenue_mismatch": 0,
                "margin_mismatch": 0,
                "cost_mismatch": 0,
                "has_totals_error": False,
                # Aggregated fields
                "items_count": 0,  # Will be updated when items are processed
                "total_quantity": 0,  # Will be updated when items are processed
            }

            # Use upsert to handle conflicts
            stmt = insert(ReadModelDeal).values(**read_deal_data)
            stmt = stmt.on_conflict_do_update(index_elements=["deal_key"], set_=stmt.excluded)

            await self.session.execute(stmt)

            # Create audit entry
            await self._create_audit_entry(
                entity_type="deal",
                entity_id=deal.id,
                entity_key=deal.deal_key,
                change_type="INSERT",
                event_id=full_event["event_id"],
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id"),
            )

            logger.debug(f"Created read model for deal {deal.deal_key}")

        except Exception as e:
            logger.error(f"Failed to create deal read model: {e}")
            raise

    async def _update_deal_read_model(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Update existing deal read model."""
        try:
            deal_data = event_data.get("deal", {})
            deal = Deal.model_validate(deal_data)

            # Safely handle period - convert to Period if needed
            period = deal.period
            if isinstance(period, dict):
                from domain.value_objects import Period
                try:
                    period = Period.model_validate(period)
                except Exception as e:
                    logger.warning(f"Failed to validate period from dict {period}: {e}, using default")
                    period = Period(month="Январь", year="2025", full_name="Январь 2025")
            elif hasattr(period, 'month'):
                # Already a Period object
                pass
            else:
                # Fallback - use valid values
                from domain.value_objects import Period
                logger.warning(f"Invalid period object {period}, using default")
                period = Period(month="Январь", year="2025", full_name="Январь 2025")

            # Get changes from event
            changes = event_data.get("changes", {})

            # Update read model
            update_data = {
                "hash_key": str(deal.hash_key),
                "client_name": deal.client_name,
                "invoice_info": deal.invoice_info,
                "invoice_number": deal.invoice_number,
                "invoice_date": deal.invoice_date,
                "period_month": period.month,
                "period_year": period.year,
                "period_full_name": str(period),
                "is_shipped": self._status_to_db(deal.is_shipped),
                "is_paid": self._status_to_db(deal.is_paid),
                "upd_number": deal.upd_number,
                "seller": deal.seller,
                "total_revenue_amount": deal.total_revenue.amount if deal.total_revenue else None,
                "total_margin_amount": deal.total_margin.amount if deal.total_margin else None,
                "total_cost_amount": deal.total_cost.amount if deal.total_cost else None,
                "kickback_amount_value": deal.kickback_amount.amount
                if deal.kickback_amount
                else None,
                "items_count": len(deal.items),
                "total_quantity": sum(item.quantity or 0 for item in deal.items),
                "version": ReadModelDeal.version + 1,
            }

            stmt = update(ReadModelDeal).where(ReadModelDeal.id == deal.id).values(**update_data)

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
                    sync_session_id=full_event.get("metadata", {}).get("sync_session_id"),
                )

            logger.debug(f"Updated read model for deal {deal.deal_key}")

        except Exception as e:
            logger.error(f"Failed to update deal read model: {e}")
            raise

    async def _delete_deal_read_model(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
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
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id"),
            )

            logger.debug(f"Deleted read model for deal {deal_key}")

        except Exception as e:
            logger.error(f"Failed to delete deal read model: {e}")
            raise

    async def _create_deal_item_read_model(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Create read model entry for new deal item."""
        try:
            # Handle both formats: event_data.deal_item and direct event_data
            item_data = event_data.get("deal_item", event_data)
            
            # Create a DealItem object from the event data
            from domain.models import DealItem
            from domain.value_objects import Money, SignedMoney
            
            # Extract prices data
            prices = item_data.get("prices", {})
            
            # Create Money objects for pricing data
            purchase_data = prices.get("purchase")
            purchase_price = Money(amount=Decimal(purchase_data)) if purchase_data else None
            
            sale_data = prices.get("sale")
            sale_price = Money(amount=Decimal(sale_data)) if sale_data else None
            
            revenue_data = prices.get("revenue")
            revenue = Money(amount=Decimal(revenue_data)) if revenue_data else None
            
            margin_data = prices.get("margin")
            margin = SignedMoney(amount=Decimal(margin_data)) if margin_data else None
            
            cost_data = prices.get("cost")
            cost = Money(amount=Decimal(cost_data)) if cost_data else None

            # Create DealItem object
            item = DealItem(
                id=uuid.UUID(item_data["item_id"]),
                deal_id=uuid.UUID(item_data["deal_id"]),
                item_key=item_data.get("product_name", ""),  # Use product_name as item_key
                product_name=item_data["product_name"],
                supplier_name=item_data.get("supplier_name", ""),
                pickup_date=item_data.get("pickup_date"),
                quantity=Decimal(item_data["quantity"]) if item_data.get("quantity") else None,
                purchase_price=purchase_price,
                sale_price=sale_price,
                revenue=revenue,
                margin=margin,
                cost=cost,
                position_number=item_data.get("position_number", 1),  # Add position_number from event data
            )

            # Get deal context for denormalization
            deal_context = await self._get_deal_context(item.deal_id)

            # HYBRID APPROACH: Check if parent deal exists
            if not deal_context:
                # Defer processing - parent deal not found
                reason = f"Parent deal {item.deal_id} not found in read model (DealCreated event may not be processed yet)"
                await self.deferred_queue.add_event(full_event, reason)
                logger.warning(
                    f"DealItemAdded event deferred: parent deal {item.deal_id} not found. "
                    f"Event will be retried after DealCreated is processed."
                )
                return

            # Create read model entry
            deal_key = deal_context.get("deal_key", "")
            read_position_data = {
                "id": item.id,
                "deal_id": item.deal_id,
                "deal_key": deal_key,
                # Item info with position number and full hash key
                "position_number": item.position_number if item.position_number is not None else 1,
                "hash_key": str(item.get_full_hash_key(deal_key)),
                "product_name": item.product_name,
                "supplier_name": item.supplier_name,
                "pickup_date": item.pickup_date,
                # Quantities and pricing
                "quantity": item.quantity,
                "purchase_price_amount": item.purchase_price.amount if item.purchase_price else None,
                "sale_price_amount": item.sale_price.amount if item.sale_price else None,
                "revenue_amount": item.revenue.amount if item.revenue else None,
                "margin_amount": item.margin.amount if item.margin else None,
                "cost_amount": item.cost.amount if item.cost else None,
                # Deal context (denormalized)
                "client_name": deal_context.get("client_name", ""),
                "period_month": deal_context.get("period_month", ""),
                "period_year": deal_context.get("period_year", ""),
            }

            # NEW LOGIC: Use version-based approach to prevent duplication
            # When same hash_key exists but with different deal_id, we need to handle it properly
            
            # Step 1: Check if there's already an active position with this hash_key
            existing_active = await self.session.execute(
                select(ReadModelPosition)
                .where(
                    ReadModelPosition.hash_key == read_position_data["hash_key"],
                    ReadModelPosition.is_active == True
                )
            )
            existing_position = existing_active.scalar_one_or_none()
            
            if existing_position:
                # Step 2: If position exists and it's the same deal_id - update it
                if existing_position.deal_id == read_position_data["deal_id"]:
                    # Same deal, same position - just update
                    update_data = {k: v for k, v in read_position_data.items() if k not in ["id", "hash_key"]}
                    update_data["version"] = existing_position.version + 1
                    
                    stmt = (
                        update(ReadModelPosition)
                        .where(ReadModelPosition.id == existing_position.id)
                        .values(**update_data)
                    )
                    await self.session.execute(stmt)
                    
                else:
                    # Step 3: Different deal_id with same hash_key - version control
                    # Deactivate old position
                    old_version = existing_position.version
                    await self.session.execute(
                        update(ReadModelPosition)
                        .where(ReadModelPosition.id == existing_position.id)
                        .values(is_active=False, version=old_version + 1)
                    )
                    
                    # Create new position with incremented version
                    read_position_data["version"] = old_version + 2
                    read_position_data["is_active"] = True
                    
                    stmt = insert(ReadModelPosition).values(**read_position_data)
                    await self.session.execute(stmt)
            else:
                # Step 4: No existing active position - create new one
                read_position_data["version"] = 1
                read_position_data["is_active"] = True
                
                stmt = insert(ReadModelPosition).values(**read_position_data)
                await self.session.execute(stmt)

            # Create audit entry
            await self._create_audit_entry(
                entity_type="position",
                entity_id=item.id,
                entity_key=item.item_key,
                change_type="INSERT",
                event_id=full_event["event_id"],
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id"),
            )

            # Recalculate totals for the deal after adding position
            await self._recalculate_totals(item.deal_id)

            logger.debug(f"Created read model for position {item.item_key}")

        except Exception as e:
            logger.error(f"Failed to create deal item read model: {e}")
            raise

    async def _update_deal_item_read_model(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Update existing deal item read model."""
        try:
            item_data = event_data.get("deal_item", {})
            item = DealItem.model_validate(item_data)

            # Get changes from event
            changes = event_data.get("changes", {})

            # Get deal context for denormalization
            deal_context = await self._get_deal_context(item.deal_id)

            # NEW UPDATE LOGIC: Handle hash_key changes with versioning
            new_hash_key = str(item.hash_key)
            
            # Get current position
            current_position = await self.session.execute(
                select(ReadModelPosition).where(ReadModelPosition.id == item.id)
            )
            current = current_position.scalar_one_or_none()
            
            if not current:
                logger.warning(f"Position {item.id} not found for update")
                return
                
            if current.hash_key == new_hash_key:
                # Hash didn't change - simple update
                update_data = {
                    "product_name": item.product_name,
                    "supplier_name": item.supplier_name,
                    "pickup_date": item.pickup_date,
                    "quantity": item.quantity,
                    "purchase_price_amount": item.purchase_price.amount if item.purchase_price else None,
                    "sale_price_amount": item.sale_price.amount if item.sale_price else None,
                    "revenue_amount": item.revenue.amount if item.revenue else None,
                    "margin_amount": item.margin.amount if item.margin else None,
                    "cost_amount": item.cost.amount if item.cost else None,
                    # Update denormalized deal context
                    "client_name": deal_context.get("client_name", ""),
                    "period_month": deal_context.get("period_month", ""),
                    "period_year": deal_context.get("period_year", ""),
                    "version": current.version + 1,
                }
                
                stmt = (
                    update(ReadModelPosition)
                    .where(ReadModelPosition.id == item.id)
                    .values(**update_data)
                )
                await self.session.execute(stmt)
                
            else:
                # Hash changed - need to create new version and deactivate old
                # Step 1: Deactivate current position
                await self.session.execute(
                    update(ReadModelPosition)
                    .where(ReadModelPosition.id == item.id)
                    .values(is_active=False, version=current.version + 1)
                )
                
                # Step 2: Check if new hash_key already exists as active
                existing_new = await self.session.execute(
                    select(ReadModelPosition)
                    .where(
                        ReadModelPosition.hash_key == new_hash_key,
                        ReadModelPosition.is_active == True
                    )
                )
                existing_new_position = existing_new.scalar_one_or_none()
                
                if existing_new_position:
                    # Deactivate conflicting position
                    await self.session.execute(
                        update(ReadModelPosition)
                        .where(ReadModelPosition.id == existing_new_position.id)
                        .values(is_active=False, version=existing_new_position.version + 1)
                    )
                    next_version = max(current.version, existing_new_position.version) + 2
                else:
                    next_version = current.version + 2
                
                # Step 3: Create new position with updated hash
                new_position_data = {
                    "id": item.id,  # Keep same ID to maintain entity identity
                    "deal_id": item.deal_id,
                    "deal_key": deal_context.get("deal_key", ""),
                    "position_number": current.position_number,
                    "hash_key": new_hash_key,
                    "product_name": item.product_name,
                    "supplier_name": item.supplier_name,
                    "pickup_date": item.pickup_date,
                    "quantity": item.quantity,
                    "purchase_price_amount": item.purchase_price.amount if item.purchase_price else None,
                    "sale_price_amount": item.sale_price.amount if item.sale_price else None,
                    "revenue_amount": item.revenue.amount if item.revenue else None,
                    "margin_amount": item.margin.amount if item.margin else None,
                    "cost_amount": item.cost.amount if item.cost else None,
                    "client_name": deal_context.get("client_name", ""),
                    "period_month": deal_context.get("period_month", ""),
                    "period_year": deal_context.get("period_year", ""),
                    "is_active": True,
                    "version": next_version,
                }
                
                stmt = insert(ReadModelPosition).values(**new_position_data)
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
                    sync_session_id=full_event.get("metadata", {}).get("sync_session_id"),
                )

            # Recalculate totals for the deal after updating position
            await self._recalculate_totals(item.deal_id)

            logger.debug(f"Updated read model for position {item.item_key}")

        except Exception as e:
            logger.error(f"Failed to update deal item read model: {e}")
            raise

    async def _delete_deal_item_read_model(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
    ) -> None:
        """Soft delete deal item read model."""
        try:
            item_id = uuid.UUID(event_data.get("deal_item_id"))
            item_key = event_data.get("item_key", "")

            # Get deal_id before deleting
            result = await self.session.execute(
                select(ReadModelPosition.deal_id).where(ReadModelPosition.id == item_id)
            )
            deal_id = result.scalar()

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
                sync_session_id=full_event.get("metadata", {}).get("sync_session_id"),
            )

            # Recalculate totals for the deal after deleting position
            if deal_id:
                await self._recalculate_totals(deal_id)

            logger.debug(f"Deleted read model for position {item_key}")

        except Exception as e:
            logger.error(f"Failed to delete deal item read model: {e}")
            raise

    async def _update_stats_after_sync(
        self, event_data: dict[str, Any], full_event: dict[str, Any]
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
                paid_deals_count=stats.get("paid_deals", 0),
            )

            # Use upsert to handle conflicts
            from sqlalchemy.dialects.postgresql import insert

            stmt = insert(ReadModelStats).values(**daily_stats.__dict__)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stat_type", "stat_date", "dimension_type", "dimension_value"],
                set_={
                    "deals_count": stmt.excluded.deals_count,
                    "positions_count": stmt.excluded.positions_count,
                    "total_revenue": stmt.excluded.total_revenue,
                    "total_margin": stmt.excluded.total_margin,
                    "total_cost": stmt.excluded.total_cost,
                    "total_quantity": stmt.excluded.total_quantity,
                    "shipped_deals_count": stmt.excluded.shipped_deals_count,
                    "paid_deals_count": stmt.excluded.paid_deals_count,
                    "calculated_at": func.now(),
                },
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

    async def _recalculate_totals(self, deal_id: uuid.UUID) -> None:
        """Recalculate aggregated totals and detect mismatches for a deal."""
        from decimal import Decimal
        from sqlalchemy import select, func, update, and_

        # 1. Collect aggregates from positions
        result = await self.session.execute(
            select(
                func.count(ReadModelPosition.id),
                func.coalesce(func.sum(ReadModelPosition.quantity), 0),
                func.coalesce(func.sum(ReadModelPosition.revenue_amount), 0),
                func.coalesce(func.sum(ReadModelPosition.margin_amount), 0),
                func.coalesce(func.sum(ReadModelPosition.cost_amount), 0),
            ).where(
                and_(
                    ReadModelPosition.deal_id == deal_id,
                    ReadModelPosition.is_active.is_(True),
                )
            )
        )
        items_cnt, qty, rev, mar, cost = result.one()

        # 2. Get total amounts from Excel
        src_row = await self.session.execute(
            select(
                ReadModelDeal.total_revenue_amount,
                ReadModelDeal.total_margin_amount,
                ReadModelDeal.total_cost_amount,
            ).where(ReadModelDeal.id == deal_id)
        )
        src_rev, src_mar, src_cost = src_row.one()

        # 3. Compute deltas
        def _delta(src: Decimal | None, calc: Decimal) -> Decimal:
            return abs((src or Decimal("0")) - calc)

        delta_rev = _delta(src_rev, rev)
        delta_mar = _delta(src_mar, mar)
        delta_cost = _delta(src_cost, cost)

        has_error = any(d > Decimal("0.01") for d in (delta_rev, delta_mar, delta_cost))

        # 4. Update deal row
        await self.session.execute(
            update(ReadModelDeal)
            .where(ReadModelDeal.id == deal_id)
            .values(
                items_count=items_cnt,
                total_quantity=qty,
                calc_revenue_amount=rev,
                calc_margin_amount=mar,
                calc_cost_amount=cost,
                revenue_mismatch=delta_rev,
                margin_mismatch=delta_mar,
                cost_mismatch=delta_cost,
                has_totals_error=has_error,
            )
        )

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
        new_value: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Create audit trail entry."""
        try:
            # Log detailed audit info for sync operations
            if additional_data:
                logger.debug(f"Audit entry: {entity_type} {entity_id} {change_type} - {additional_data}")
            else:
                logger.debug(f"Audit entry: {entity_type} {entity_id} {change_type}")
            return
            
            audit_entry = ReadModelAudit(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_key=entity_key,
                change_type=change_type,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                sync_session_id=sync_session_id or uuid.uuid4(),
                event_id=event_id,
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
