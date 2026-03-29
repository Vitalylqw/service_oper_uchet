"""
Atomic Deal Synchronization Logic.

Implements atomic deal rewrite approach:
1. DELETE existing deal (FK CASCADE removes positions)
2. INSERT deal with full data
3. INSERT all positions from Excel

No UPSERT, no versioning, no soft deletes.
Full history preserved in event_store.
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import Deal, DealItem

from ..database.models import ReadModelDeal, ReadModelPosition


class SimplePositionSync:
    """
    Atomic deal synchronization: DELETE deal + INSERT deal + INSERT positions.

    Transaction management is handled by the caller (ReadModelBuilder).
    This class never calls session.commit().
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_deal_positions(
        self,
        deal: Deal,
        deal_context: dict[str, Any],
        sync_session_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """
        Atomically rewrite deal with all positions.

        Steps:
            1. DELETE deal from read_deals (FK CASCADE removes positions)
            2. INSERT deal into read_deals
            3. INSERT each position into read_positions

        Args:
            deal: Deal object with all current positions from Excel.
            deal_context: Deal context for position denormalization.
            sync_session_id: Sync session ID for logging.

        Returns:
            Dict with sync statistics: {'deleted': N, 'inserted_deal': 1, 'inserted_positions': N}
        """
        deal_key = deal_context.get("deal_key", "")
        logger.info(
            f"Starting atomic deal sync for {deal_key} "
            f"with {len(deal.items)} positions"
        )

        stats: dict[str, int] = {
            "deleted": 0,
            "inserted_deal": 0,
            "inserted_positions": 0,
        }

        deleted = await self._delete_deal(deal.id)
        stats["deleted"] = 1 if deleted else 0

        await self._insert_deal(deal, deal_context)
        stats["inserted_deal"] = 1

        if deal.items:
            await self._insert_positions_batch(deal.items, deal_context)
            stats["inserted_positions"] = len(deal.items)

        logger.info(f"Atomic deal sync completed for {deal_key}: {stats}")
        return stats

    async def _delete_deal(self, deal_id: uuid.UUID) -> bool:
        """Delete deal from read_deals; FK CASCADE removes positions.

        Returns:
            True if a row was deleted, False if deal did not exist.
        """
        result = await self.session.execute(
            delete(ReadModelDeal).where(ReadModelDeal.id == deal_id)
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Deleted deal {deal_id} (cascade removed positions)")
        return deleted

    async def _insert_deal(
        self, deal: Deal, deal_context: dict[str, Any]
    ) -> None:
        """Insert deal into read_deals."""
        from domain.value_objects.common import Status

        status_map = {
            Status.PENDING: "pending",
            Status.PARTIAL: "partial",
            Status.COMPLETED: "completed",
            Status.PAID: "paid",
            Status.SHIPPED: "shipped",
            Status.CANCELLED: "cancelled",
            Status.FAILED: "failed",
        }

        def _status_to_db(status: Any) -> str | None:
            if status is None:
                return None
            if isinstance(status, Status):
                return status_map.get(status, "pending")
            if isinstance(status, str):
                lower = status.lower().strip()
                if lower in status_map.values():
                    return lower
                if lower in ("да", "yes", "true"):
                    return "completed"
                return "pending"
            return "pending"

        deal_data = {
            "id": deal.id,
            "deal_key": deal.deal_key,
            "hash_key": str(deal.hash_key),
            "client_name": deal.client_name,
            "invoice_info": deal.invoice_info,
            "invoice_number": deal.invoice_number,
            "invoice_date": deal.invoice_date,
            "period_month": deal.period.month,
            "period_year": deal.period.year,
            "period_full_name": str(deal.period),
            "is_shipped": _status_to_db(deal.is_shipped),
            "is_paid": _status_to_db(deal.is_paid),
            "upd_number": deal.upd_number,
            "seller": deal.seller,
            "total_revenue_amount": (
                deal.total_revenue.amount if deal.total_revenue else None
            ),
            "total_margin_amount": (
                deal.total_margin.amount if deal.total_margin else None
            ),
            "total_cost_amount": (
                deal.total_cost.amount if deal.total_cost else None
            ),
            "kickback_amount_value": (
                deal.kickback_amount.amount if deal.kickback_amount else None
            ),
            "items_count": len(deal.items),
            "total_quantity": sum(
                item.quantity or 0 for item in deal.items
            ),
        }

        stmt = insert(ReadModelDeal).values(**deal_data)
        await self.session.execute(stmt)
        logger.debug(f"Inserted deal {deal.deal_key}")

    async def _insert_position(
        self, item: DealItem, deal_context: dict[str, Any]
    ) -> None:
        """Insert single position into read_positions."""
        position_data = self._prepare_position_data(item, deal_context)
        stmt = insert(ReadModelPosition).values(**position_data)
        await self.session.execute(stmt)

    async def _insert_positions_batch(
        self, items: list[DealItem], deal_context: dict[str, Any]
    ) -> None:
        """Insert all deal positions with a single batch statement."""
        position_rows = [
            self._prepare_position_data(item, deal_context)
            for item in items
        ]
        stmt = insert(ReadModelPosition).values(position_rows)
        await self.session.execute(stmt)

    def _prepare_position_data(
        self, item: DealItem, deal_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare position data dict for database insertion."""
        deal_key = deal_context.get("deal_key", "")

        return {
            "id": item.id,
            "deal_id": item.deal_id,
            "deal_key": deal_key,
            "position_number": (
                item.position_number if item.position_number is not None else 1
            ),
            "hash_key": str(item.get_full_hash_key(deal_key)),
            "product_name": item.product_name,
            "supplier_name": item.supplier_name,
            "pickup_date": item.pickup_date,
            "quantity": item.quantity,
            "purchase_price_amount": (
                item.purchase_price.amount if item.purchase_price else None
            ),
            "sale_price_amount": (
                item.sale_price.amount if item.sale_price else None
            ),
            "revenue_amount": (
                item.revenue.amount if item.revenue else None
            ),
            "margin_amount": (
                item.margin.amount if item.margin else None
            ),
            "cost_amount": (
                item.cost.amount if item.cost else None
            ),
            "client_name": deal_context.get("client_name", ""),
            "period_month": deal_context.get("period_month", ""),
            "period_year": deal_context.get("period_year", ""),
        }
