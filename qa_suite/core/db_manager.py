"""
Database Manager for QA Suite.

Provides database operations for testing: clearing data, snapshots,
aggregate metrics collection, and state queries.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.infrastructure.database.models import (
    Base,
    EventStoreModel,
    ReadModelAudit,
    ReadModelDeal,
    ReadModelPosition,
    ReadModelStats,
    SyncSessionModel,
)

from .models import AggregateMetrics, DBSnapshot


class DBManager:
    """
    Manager for database operations in QA Suite.

    Provides methods for clearing data, taking snapshots, and collecting metrics.
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize DBManager.

        Args:
            database_url: Async database connection URL.
        """
        self._database_url = database_url
        self._engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_session(self) -> AsyncSession:
        """Get a new async session."""
        return self._session_factory()

    async def clear_all_data(self) -> None:
        """
        Clear all test-related data from database.

        Deletes data from: read_positions, read_deals, event_store,
        sync_sessions, read_audit, read_stats.
        """
        async with self._session_factory() as session:
            try:
                # Delete in order respecting foreign key constraints
                await session.execute(delete(ReadModelPosition))
                await session.execute(delete(ReadModelAudit))
                await session.execute(delete(ReadModelStats))
                await session.execute(delete(ReadModelDeal))
                await session.execute(delete(EventStoreModel))
                await session.execute(delete(SyncSessionModel))

                await session.commit()
                logger.info("Cleared all data from database")

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to clear database: {e}")
                raise

    async def clear_period_data(self, period_month: str, period_year: str) -> int:
        """
        Clear data for a specific period.

        Args:
            period_month: Month name (e.g., "Май")
            period_year: Year (e.g., "2025")

        Returns:
            Number of deals deleted.
        """
        async with self._session_factory() as session:
            try:
                # Get deals in period
                result = await session.execute(
                    select(ReadModelDeal.id).where(
                        ReadModelDeal.period_month == period_month,
                        ReadModelDeal.period_year == period_year,
                    )
                )
                deal_ids = [row[0] for row in result.fetchall()]

                if deal_ids:
                    # Delete positions first (cascade should handle this, but explicit)
                    await session.execute(
                        delete(ReadModelPosition).where(
                            ReadModelPosition.deal_id.in_(deal_ids)
                        )
                    )
                    # Delete deals
                    await session.execute(
                        delete(ReadModelDeal).where(ReadModelDeal.id.in_(deal_ids))
                    )
                    await session.commit()
                    logger.info(
                        f"Cleared {len(deal_ids)} deals from period "
                        f"{period_month} {period_year}"
                    )
                    return len(deal_ids)

                return 0

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to clear period data: {e}")
                raise

    async def get_snapshot(self) -> DBSnapshot:
        """
        Take a snapshot of current database state.

        Returns:
            DBSnapshot with all deals, positions, and events.
        """
        async with self._session_factory() as session:
            # Get all deals
            deals_result = await session.execute(select(ReadModelDeal))
            deals = [
                {
                    "id": str(d.id),
                    "deal_key": d.deal_key,
                    "hash_key": d.hash_key,
                    "client_name": d.client_name,
                    "invoice_info": d.invoice_info,
                    "period_month": d.period_month,
                    "period_year": d.period_year,
                    "is_shipped": d.is_shipped,
                    "is_paid": d.is_paid,
                    "seller": d.seller,
                    "total_revenue_amount": str(d.total_revenue_amount)
                    if d.total_revenue_amount
                    else None,
                    "total_margin_amount": str(d.total_margin_amount)
                    if d.total_margin_amount
                    else None,
                    "total_cost_amount": str(d.total_cost_amount)
                    if d.total_cost_amount
                    else None,
                    "items_count": d.items_count,
                }
                for d in deals_result.scalars()
            ]

            # Get all positions
            positions_result = await session.execute(select(ReadModelPosition))
            positions = [
                {
                    "id": str(p.id),
                    "deal_id": str(p.deal_id),
                    "deal_key": p.deal_key,
                    "position_number": p.position_number,
                    "hash_key": p.hash_key,
                    "product_name": p.product_name,
                    "supplier_name": p.supplier_name,
                    "quantity": str(p.quantity) if p.quantity else None,
                    "purchase_price_amount": str(p.purchase_price_amount)
                    if p.purchase_price_amount
                    else None,
                    "sale_price_amount": str(p.sale_price_amount)
                    if p.sale_price_amount
                    else None,
                }
                for p in positions_result.scalars()
            ]

            # Get events
            events_result = await session.execute(select(EventStoreModel))
            events = [
                {
                    "id": e.id,
                    "event_id": str(e.event_id),
                    "aggregate_id": str(e.aggregate_id),
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                }
                for e in events_result.scalars()
            ]

            metrics = await self.get_aggregates()

            return DBSnapshot(
                timestamp=datetime.now(),
                deals=deals,
                positions=positions,
                events=events,
                metrics=metrics,
            )

    async def get_aggregates(self) -> AggregateMetrics:
        """
        Collect aggregate metrics from database.

        Returns:
            AggregateMetrics with counts and sums.
        """
        async with self._session_factory() as session:
            metrics = AggregateMetrics()

            # Total deals
            result = await session.execute(
                select(func.count()).select_from(ReadModelDeal)
            )
            metrics.total_deals = result.scalar() or 0

            # Total positions
            result = await session.execute(
                select(func.count()).select_from(ReadModelPosition)
            )
            metrics.total_positions = result.scalar() or 0

            # Sum of financial values
            result = await session.execute(
                select(
                    func.coalesce(func.sum(ReadModelDeal.total_revenue_amount), 0),
                    func.coalesce(func.sum(ReadModelDeal.total_margin_amount), 0),
                    func.coalesce(func.sum(ReadModelDeal.total_cost_amount), 0),
                )
            )
            row = result.fetchone()
            if row:
                metrics.total_revenue_sum = Decimal(str(row[0]))
                metrics.total_margin_sum = Decimal(str(row[1]))
                metrics.total_cost_sum = Decimal(str(row[2]))

            # Deals by period
            result = await session.execute(
                select(
                    ReadModelDeal.period_full_name,
                    func.count().label("count"),
                ).group_by(ReadModelDeal.period_full_name)
            )
            metrics.deals_by_period = {
                row.period_full_name: row.count for row in result.fetchall()
            }

            # Positions by period
            result = await session.execute(
                select(
                    ReadModelPosition.period_month,
                    ReadModelPosition.period_year,
                    func.count().label("count"),
                ).group_by(
                    ReadModelPosition.period_month, ReadModelPosition.period_year
                )
            )
            metrics.positions_by_period = {
                f"{row.period_month} {row.period_year}": row.count
                for row in result.fetchall()
            }

            # Deals with errors
            result = await session.execute(
                select(func.count())
                .select_from(ReadModelDeal)
                .where(ReadModelDeal.has_totals_error == True)
            )
            metrics.deals_with_errors = result.scalar() or 0

            # Unique clients
            result = await session.execute(
                select(func.count(func.distinct(ReadModelDeal.client_name)))
            )
            metrics.unique_clients = result.scalar() or 0

            # Unique sellers
            result = await session.execute(
                select(func.count(func.distinct(ReadModelDeal.seller)))
            )
            metrics.unique_sellers = result.scalar() or 0

            # Total events
            result = await session.execute(
                select(func.count()).select_from(EventStoreModel)
            )
            metrics.total_events = result.scalar() or 0

            # Events by type
            result = await session.execute(
                select(
                    EventStoreModel.event_type,
                    func.count().label("count"),
                ).group_by(EventStoreModel.event_type)
            )
            metrics.events_by_type = {
                row.event_type: row.count for row in result.fetchall()
            }

            return metrics

    async def count_deals_by_period(self, month: str, year: str) -> int:
        """Count deals in a specific period."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(ReadModelDeal)
                .where(
                    ReadModelDeal.period_month == month,
                    ReadModelDeal.period_year == year,
                )
            )
            return result.scalar() or 0

    async def count_positions_by_period(self, month: str, year: str) -> int:
        """Count positions in a specific period."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(ReadModelPosition)
                .where(
                    ReadModelPosition.period_month == month,
                    ReadModelPosition.period_year == year,
                )
            )
            return result.scalar() or 0

    async def count_positions_by_deal(self, deal_key: str) -> int:
        """Count positions for a specific deal."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(ReadModelPosition)
                .where(ReadModelPosition.deal_key == deal_key)
            )
            return result.scalar() or 0

    async def get_deal_by_key(self, deal_key: str) -> Optional[ReadModelDeal]:
        """Get deal by its business key."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ReadModelDeal).where(ReadModelDeal.deal_key == deal_key)
            )
            return result.scalar_one_or_none()

    async def deal_exists(self, deal_key: str) -> bool:
        """Check if deal exists."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(ReadModelDeal)
                .where(ReadModelDeal.deal_key == deal_key)
            )
            count = result.scalar() or 0
            return count > 0

    async def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get events of specific type."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(EventStoreModel).where(
                    EventStoreModel.event_type == event_type
                )
            )
            return [
                {
                    "id": e.id,
                    "event_id": str(e.event_id),
                    "aggregate_id": str(e.aggregate_id),
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in result.scalars()
            ]

    async def get_recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get most recent events."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(EventStoreModel)
                .order_by(EventStoreModel.sequence_number.desc())
                .limit(limit)
            )
            return [
                {
                    "id": e.id,
                    "event_id": str(e.event_id),
                    "aggregate_id": str(e.aggregate_id),
                    "event_type": e.event_type,
                    "sequence_number": e.sequence_number,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in result.scalars()
            ]

    async def close(self) -> None:
        """Close database connections."""
        await self._engine.dispose()


def compute_aggregate_diff(
    before: AggregateMetrics, after: AggregateMetrics
) -> dict[str, Any]:
    """
    Compute difference between two aggregate metrics states.

    Args:
        before: Metrics before operation.
        after: Metrics after operation.

    Returns:
        Dictionary with differences.
    """
    return {
        "deals_diff": after.total_deals - before.total_deals,
        "positions_diff": after.total_positions - before.total_positions,
        "revenue_diff": str(after.total_revenue_sum - before.total_revenue_sum),
        "margin_diff": str(after.total_margin_sum - before.total_margin_sum),
        "cost_diff": str(after.total_cost_sum - before.total_cost_sum),
        "events_diff": after.total_events - before.total_events,
        "deals_with_errors_diff": (
            after.deals_with_errors - before.deals_with_errors
        ),
        "new_periods": [
            k for k in after.deals_by_period if k not in before.deals_by_period
        ],
        "removed_periods": [
            k for k in before.deals_by_period if k not in after.deals_by_period
        ],
    }
