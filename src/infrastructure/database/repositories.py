"""
Repository implementations for database access.

Contains concrete implementations of domain repository interfaces.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.interfaces import DealRepository, ReadModelRepository, SyncSessionRepository
from domain.models import Deal, SyncSession
from domain.value_objects import Money, Period, SignedMoney, Status
from infrastructure.database.models import (
    ReadModelDeal,
    ReadModelPosition,
    SyncSessionModel,
)
from infrastructure.mappers.deal_item_mapper import from_read_position


class DealRepositoryImplementation(DealRepository):
    """
    PostgreSQL implementation of Deal repository.

    Uses read models for fast queries and event store for persistence.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def get_by_id(self, deal_id: uuid.UUID) -> Deal | None:
        """Get deal by ID from read model."""
        try:
            query = select(ReadModelDeal).where(ReadModelDeal.id == deal_id)
            result = await self.session.execute(query)
            deal_model = result.scalar_one_or_none()

            if not deal_model:
                return None

            return await self._read_model_to_domain(deal_model)

        except Exception as e:
            logger.error(f"Failed to get deal by id {deal_id}: {e}")
            raise

    async def get_by_key(self, deal_key: str) -> Deal | None:
        """Get deal by business key from read model."""
        try:
            query = select(ReadModelDeal).where(ReadModelDeal.deal_key == deal_key)
            result = await self.session.execute(query)
            deal_model = result.scalar_one_or_none()

            if not deal_model:
                return None

            return await self._read_model_to_domain(deal_model)

        except Exception as e:
            logger.error(f"Failed to get deal by key {deal_key}: {e}")
            raise

    async def find_by_client(self, client_name: str) -> list[Deal]:
        """Find deals by client name from read model."""
        try:
            query = (
                select(ReadModelDeal)
                .where(ReadModelDeal.client_name.ilike(f"%{client_name}%"))
                .order_by(ReadModelDeal.created_at.desc())
            )

            result = await self.session.execute(query)
            deal_models = result.scalars().all()

            deals = []
            for deal_model in deal_models:
                deal = await self._read_model_to_domain(deal_model)
                deals.append(deal)

            logger.debug(f"Found {len(deals)} deals for client '{client_name}'")
            return deals

        except Exception as e:
            logger.error(f"Failed to find deals by client {client_name}: {e}")
            raise

    async def find_by_period(self, period_month: str, period_year: str) -> list[Deal]:
        """Find deals by period from read model."""
        try:
            query = (
                select(ReadModelDeal)
                .where(ReadModelDeal.period_month == period_month)
                .where(ReadModelDeal.period_year == period_year)
                .order_by(ReadModelDeal.created_at.desc())
            )

            result = await self.session.execute(query)
            deal_models = result.scalars().all()

            deals = []
            for deal_model in deal_models:
                deal = await self._read_model_to_domain(deal_model)
                deals.append(deal)

            logger.debug(f"Found {len(deals)} deals for period {period_month} {period_year}")
            return deals

        except Exception as e:
            logger.error(f"Failed to find deals by period {period_month} {period_year}: {e}")
            raise

    async def find_all_paginated(
        self,
        page: int,
        limit: int,
        filters: dict | None = None
    ) -> dict:
        """Find all deals with pagination and filters."""
        try:
            # Base query
            query = select(ReadModelDeal)

            # Apply filters
            if filters:
                if filters.get("client_name"):
                    query = query.where(
                        ReadModelDeal.client_name.ilike(f"%{filters['client_name']}%")
                    )

                if filters.get("seller"):
                    query = query.where(
                        ReadModelDeal.seller.ilike(f"%{filters['seller']}%")
                    )

                if filters.get("is_shipped") is not None:
                    # Convert boolean filter to string value used in database
                    shipped_filter = str(filters["is_shipped"]).lower()
                    if shipped_filter == "true":
                        query = query.where(ReadModelDeal.is_shipped.in_( ["shipped", "completed"]))
                    elif shipped_filter == "false":
                        query = query.where(ReadModelDeal.is_shipped.in_(["pending", "partial"]))

                if filters.get("is_paid") is not None:
                    # Convert boolean filter to string value used in database
                    paid_filter = str(filters["is_paid"]).lower()
                    if paid_filter == "true":
                        query = query.where(ReadModelDeal.is_paid.in_( ["paid", "completed"]))
                    elif paid_filter == "false":
                        query = query.where(ReadModelDeal.is_paid.in_(["pending", "partial"]))

            # Count total for pagination
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()

            # Apply pagination and ordering
            query = query.order_by(ReadModelDeal.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)

            # Execute query
            result = await self.session.execute(query)
            deal_models = result.scalars().all()

            # Return read models directly for API usage
            logger.debug(f"Found {len(deal_models)} deals (page {page}, total {total})")

            return {
                "items": deal_models,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit if total > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Failed to find paginated deals: {e}")
            raise

    async def save(self, deal: Deal) -> None:
        """Save deal - this should trigger event creation (handled by application layer)."""
        # NOTE: This is a read-only repository in Event Sourcing architecture
        # Actual saving is done through events in the application layer
        logger.warning("Direct save called on DealRepository - use application services instead")

    async def save_batch(self, deals: list[Deal]) -> None:
        """Save multiple deals - should use application layer."""
        logger.warning(
            "Direct save_batch called on DealRepository - use application services instead"
        )

    async def delete(self, deal_id: uuid.UUID) -> None:
        """Hard delete deal (positions are deleted by FK cascade)."""
        try:
            await self.session.execute(
                delete(ReadModelDeal).where(ReadModelDeal.id == deal_id)
            )
            logger.debug(f"Hard deleted deal {deal_id}")

        except Exception as e:
            logger.error(f"Failed to delete deal {deal_id}: {e}")
            raise

    async def get_all_keys(self) -> list[str]:
        """Get all deal keys for change detection."""
        try:
            query = select(ReadModelDeal.deal_key)

            result = await self.session.execute(query)
            deal_keys = result.scalars().all()

            logger.debug(f"Retrieved {len(deal_keys)} deal keys")
            return list(deal_keys)

        except Exception as e:
            logger.error(f"Failed to get all deal keys: {e}")
            raise

    async def _read_model_to_domain(self, model: ReadModelDeal) -> Deal:
        """Convert read model to domain object."""
        # NOTE: This is a simplified conversion
        # In a full implementation, you might reconstruct from events
        # or have more sophisticated mapping logic



        # Create period
        period = Period(
            month=model.period_month, year=model.period_year, full_name=model.period_full_name
        )

        # Build deal via DealBuilder to ensure mandatory period fields are set
        from domain.builders.deal_builder import DealBuilder
        builder = DealBuilder(period=period)
        builder.client_name = model.client_name
        builder.invoice_info = model.invoice_info
        builder.seller = model.seller or "UNKNOWN"
        builder.invoice_number = model.invoice_number or None
        builder.invoice_date = model.invoice_date or None
        builder.upd_number = model.upd_number or None
        builder.is_shipped = Status.from_string(model.is_shipped) if model.is_shipped else None
        builder.is_paid = Status.from_string(model.is_paid) if model.is_paid else None
        # Money fields from read model
        builder.total_revenue = Money(amount=model.total_revenue_amount) if model.total_revenue_amount else None
        builder.total_margin = SignedMoney(amount=model.total_margin_amount) if model.total_margin_amount else None
        builder.total_cost = Money(amount=model.total_cost_amount) if model.total_cost_amount else None
        builder.kickback_amount = Money(amount=model.kickback_amount_value) if model.kickback_amount_value else None

        deal = builder.build()
        deal.set_id(model.id)

        # Set money fields
        if model.total_revenue_amount:
            deal.total_revenue = Money(
                amount=model.total_revenue_amount
            )

        if model.total_margin_amount:
            deal.total_margin = SignedMoney(
                amount=model.total_margin_amount
            )

        if model.total_cost_amount:
            deal.total_cost = Money(
                amount=model.total_cost_amount
            )

        if model.kickback_amount_value:
            deal.kickback_amount = Money(
                amount=model.kickback_amount_value
            )

        # Load items from positions table
        await self._load_deal_items(deal)

        return deal

    async def _load_deal_items(self, deal: Deal) -> None:
        """Load deal items from positions read model."""
        try:
            query = (
                select(ReadModelPosition)
                .where(ReadModelPosition.deal_id == deal.id)
                .order_by(ReadModelPosition.created_at.asc())
            )

            result = await self.session.execute(query)
            position_models = result.scalars().all()

            for position_model in position_models:
                item = from_read_position(position_model, deal)
                deal.add_item(item)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(
                "Failed to load items for deal {}: {}\n{}",
                deal.id,
                str(e),
                error_trace,
            )
            # Don't raise - deal can exist without items


class SyncSessionRepositoryImplementation(SyncSessionRepository):
    """
    PostgreSQL implementation of SyncSession repository.

    Stores sync session data directly in database table.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def get_by_id(self, session_id: uuid.UUID) -> SyncSession | None:
        """Get sync session by ID."""
        try:
            query = select(SyncSessionModel).where(SyncSessionModel.id == session_id)
            result = await self.session.execute(query)
            session_model = result.scalar_one_or_none()

            if not session_model:
                return None

            return self._model_to_domain(session_model)

        except Exception as e:
            logger.error(f"Failed to get sync session by id {session_id}: {e}")
            raise

    async def get_running_session(self) -> SyncSession | None:
        """Get currently running sync session."""
        try:
            query = (
                select(SyncSessionModel)
                .where(SyncSessionModel.status == "pending")
                .where(SyncSessionModel.started_at.isnot(None))
                .where(SyncSessionModel.finished_at.is_(None))
                .order_by(SyncSessionModel.started_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            session_model = result.scalar_one_or_none()

            if not session_model:
                return None

            return self._model_to_domain(session_model)

        except Exception as e:
            logger.error(f"Failed to get running session: {e}")
            raise

    async def get_latest_sessions(self, limit: int = 10) -> list[SyncSession]:
        """Get latest sync sessions."""
        try:
            query = (
                select(SyncSessionModel).order_by(SyncSessionModel.created_at.desc()).limit(limit)
            )

            result = await self.session.execute(query)
            session_models = result.scalars().all()

            sessions = []
            for session_model in session_models:
                session = self._model_to_domain(session_model)
                sessions.append(session)

            logger.debug(f"Retrieved {len(sessions)} latest sessions")
            return sessions

        except Exception as e:
            logger.error(f"Failed to get latest sessions: {e}")
            raise

    async def save(self, session: SyncSession) -> None:
        """Save sync session to database."""
        try:
            # Check if session exists
            existing_query = select(SyncSessionModel).where(SyncSessionModel.id == session.id)
            result = await self.session.execute(existing_query)
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # Update existing session
                await self._update_session_model(existing_model, session)
            else:
                # Create new session
                new_model = self._domain_to_model(session)
                self.session.add(new_model)

            await self.session.flush()
            logger.debug(f"Saved sync session {session.id}")

        except Exception as e:
            logger.error(f"Failed to save sync session {session.id}: {e}")
            raise

    async def save_visible(self, session: SyncSession) -> None:
        """Persist sync session in a separate committed transaction."""
        bind = self.session.bind
        if bind is None:
            raise RuntimeError("Cannot persist sync session visibly without bound engine")

        visibility_session_factory = async_sessionmaker(
            bind=bind,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

        async with visibility_session_factory() as visibility_session:
            visibility_repository = SyncSessionRepositoryImplementation(visibility_session)
            await visibility_repository.save(session)
            await visibility_session.commit()

    async def find_by_status(self, status: str) -> list[SyncSession]:
        """Find sync sessions by status."""
        try:
            query = (
                select(SyncSessionModel)
                .where(SyncSessionModel.status == status)
                .order_by(SyncSessionModel.created_at.desc())
            )

            result = await self.session.execute(query)
            session_models = result.scalars().all()

            sessions = []
            for session_model in session_models:
                session = self._model_to_domain(session_model)
                sessions.append(session)

            logger.debug(f"Found {len(sessions)} sessions with status '{status}'")
            return sessions

        except Exception as e:
            logger.error(f"Failed to find sessions by status {status}: {e}")
            raise

    async def find_by_period(self, start_date: str, end_date: str) -> list[SyncSession]:
        """Find sync sessions by date period."""
        try:
            query = (
                select(SyncSessionModel)
                .where(SyncSessionModel.created_at >= start_date)
                .where(SyncSessionModel.created_at <= end_date)
                .order_by(SyncSessionModel.created_at.desc())
            )

            result = await self.session.execute(query)
            session_models = result.scalars().all()

            sessions = []
            for session_model in session_models:
                session = self._model_to_domain(session_model)
                sessions.append(session)

            logger.debug(f"Found {len(sessions)} sessions between {start_date} and {end_date}")
            return sessions

        except Exception as e:
            logger.error(f"Failed to find sessions by period {start_date}-{end_date}: {e}")
            raise

    def _model_to_domain(self, model: SyncSessionModel) -> SyncSession:
        """Convert database model to domain object."""
        from domain.models import SyncType


        # Create sync session
        sync_session = SyncSession(sync_type=SyncType(model.sync_type), source_file_path=model.file_path)

        # Set fields
        sync_session.id = model.id
        sync_session.status = Status(model.status)
        sync_session.source_file_hash = model.file_hash
        sync_session.source_file_size = model.file_size
        sync_session.started_at = model.started_at
        sync_session.finished_at = model.finished_at
        # Convert error_message to stats.errors
        if model.error_message:
            sync_session.stats.errors.append(model.error_message)

        # Load stats if available
        if model.stats_data:
            try:
                import json
                stats_dict = json.loads(model.stats_data)

                # Update stats with data from JSON
                sync_session.stats.total_deals = stats_dict.get('total_deals', 0)
                sync_session.stats.processed_deals = stats_dict.get('processed_deals', 0)
                sync_session.stats.failed_deals = stats_dict.get('failed_deals', 0)
                sync_session.stats.total_items = stats_dict.get('total_items', 0)
                sync_session.stats.processed_items = stats_dict.get('processed_items', 0)
                sync_session.stats.failed_items = stats_dict.get('failed_items', 0)
                sync_session.stats.new_records = stats_dict.get('new_records', 0)
                sync_session.stats.updated_records = stats_dict.get('updated_records', 0)
                sync_session.stats.deleted_records = stats_dict.get('deleted_records', 0)
                sync_session.stats.errors = stats_dict.get('errors', [])
                sync_session.stats.warnings = stats_dict.get('warnings', [])

            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse stats_data for session {model.id}: {e}")
                # Keep default empty stats

        return sync_session

    def _domain_to_model(self, session: SyncSession) -> SyncSessionModel:
        """Convert domain object to database model."""
        # Convert stats to JSON
        stats_dict = {
            "total_deals": session.stats.total_deals,
            "processed_deals": session.stats.processed_deals,
            "failed_deals": session.stats.failed_deals,
            "total_items": session.stats.total_items,
            "processed_items": session.stats.processed_items,
            "failed_items": session.stats.failed_items,
            "new_records": session.stats.new_records,
            "updated_records": session.stats.updated_records,
            "deleted_records": session.stats.deleted_records,
            "errors": session.stats.errors,
            "warnings": session.stats.warnings,
        }

        model = SyncSessionModel(
            id=session.id,
            sync_type=session.sync_type.value,
            status=session.status.value,
            file_path=session.source_file_path,
            file_hash=session.source_file_hash,
            file_size=session.source_file_size,
            started_at=session.started_at,
            finished_at=session.finished_at,
            error_message="; ".join(session.stats.errors) if session.stats.errors else None,
            stats_data=json.dumps(stats_dict),
        )

        return model

    async def _update_session_model(self, model: SyncSessionModel, session: SyncSession) -> None:
        """Update existing session model with domain data."""
        model.sync_type = session.sync_type.value
        model.status = session.status.value
        model.file_path = session.source_file_path
        model.file_hash = session.source_file_hash
        model.file_size = session.source_file_size
        model.started_at = session.started_at
        model.finished_at = session.finished_at
        model.error_message = "; ".join(session.stats.errors) if session.stats.errors else None
        # Update stats_data with latest statistics
        stats_dict = {
            "total_deals": session.stats.total_deals,
            "processed_deals": session.stats.processed_deals,
            "failed_deals": session.stats.failed_deals,
            "total_items": session.stats.total_items,
            "processed_items": session.stats.processed_items,
            "failed_items": session.stats.failed_items,
            "new_records": session.stats.new_records,
            "updated_records": session.stats.updated_records,
            "deleted_records": session.stats.deleted_records,
            "errors": session.stats.errors,
            "warnings": session.stats.warnings,
        }

        model.stats_data = json.dumps(stats_dict)


class ReadModelRepositoryImplementation(ReadModelRepository):
    """
    Implementation for read model management.

    Handles rebuilding read models from events.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def rebuild_deal_read_model(self) -> None:
        """Rebuild deal read model from events."""
        # TODO: Implement read model rebuilding from event store
        logger.info("Rebuilding deal read model...")
        # This would:
        # 1. Truncate read_deals table
        # 2. Replay all Deal events from event store
        # 3. Rebuild current state
        pass

    async def rebuild_position_read_model(self) -> None:
        """Rebuild position read model from events."""
        logger.info("Rebuilding position read model...")
        pass

    async def rebuild_stats_read_model(self) -> None:
        """Rebuild stats read model from events."""
        logger.info("Rebuilding stats read model...")
        pass

    async def get_deal_stats(
        self, period_month: str | None = None, period_year: str | None = None
    ) -> dict[str, Any]:
        """Aggregate basic statistics for deals from the read model."""

        try:
            from sqlalchemy import case

            # Base condition - get all deals (no is_active field)
            conditions = []

            if period_month:
                conditions.append(ReadModelDeal.period_month == period_month)
            if period_year:
                conditions.append(ReadModelDeal.period_year == period_year)

            # Helper for filtering
            def _where(base_query):
                for cond in conditions:
                    base_query = base_query.where(cond)
                return base_query

            # Aggregate query
            query = select(
                func.count(ReadModelDeal.id).label("total_deals"),
                func.coalesce(func.sum(ReadModelDeal.total_revenue_amount), 0).label("total_revenue"),
                func.coalesce(func.sum(ReadModelDeal.total_margin_amount), 0).label("total_margin"),
                func.coalesce(
                    func.sum(
                        case((func.lower(ReadModelDeal.is_shipped).in_(["shipped", "completed"]), 1), else_=0)
                    ),
                    0,
                ).label("shipped_deals"),
                func.coalesce(
                    func.sum(
                        case((func.lower(ReadModelDeal.is_paid).in_(["paid", "completed"]), 1), else_=0)
                    ),
                    0,
                ).label("paid_deals"),
                func.coalesce(
                    func.sum(
                        case((func.lower(ReadModelDeal.is_paid).in_(["pending", "partial"]), 1), else_=0)
                    ),
                    0,
                ).label("unpaid_deals"),
                func.coalesce(
                    func.sum(
                        case((func.lower(ReadModelDeal.is_shipped).in_( ["pending", "partial"]), 1), else_=0)
                    ),
                    0,
                ).label("unshipped_deals"),
            )

            query = _where(query)

            result = await self.session.execute(query)
            stats_row = result.one()

            total_deals = stats_row.total_deals or 0
            total_revenue = stats_row.total_revenue or 0

            avg_revenue = (
                float(total_revenue) / total_deals if total_deals > 0 else 0.0
            )

            avg_profitability = (
                (float(stats_row.total_margin or 0) / float(total_revenue) * 100)
                if total_revenue > 0 else 0.0
            )

            return {
                "total_deals": total_deals,
                "total_revenue": float(total_revenue),
                "total_margin": float(stats_row.total_margin or 0),
                "shipped_deals": stats_row.shipped_deals or 0,
                "paid_deals": stats_row.paid_deals or 0,
                "avg_revenue": float(avg_revenue),
                "avg_profitability": float(avg_profitability),
                "unpaid_deals": stats_row.unpaid_deals or 0,
                "unshipped_deals": stats_row.unshipped_deals or 0,
                "period_month": period_month,
                "period_year": period_year,
            }

        except Exception as e:
            logger.error(f"Failed to get deal stats: {e}")
            raise

    async def get_position_stats(self, supplier_name: str | None = None) -> dict[str, Any]:
        """Get position statistics from read model."""
        try:
            query = select(func.count(ReadModelPosition.id).label("total_positions"))

            if supplier_name:
                query = query.where(ReadModelPosition.supplier_name.ilike(f"%{supplier_name}%"))

            result = await self.session.execute(query)
            stats = result.one()

            return {
                "total_positions": stats.total_positions,
                "supplier_name": supplier_name,
            }

        except Exception as e:
            logger.error(f"Failed to get position stats: {e}")
            raise

    async def search_deals(
        self, query: str, filters: dict[str, Any] | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Search deals with filters and pagination."""
        try:
            # Build base query (no is_active field)
            base_query = select(ReadModelDeal)

            # Add text search
            if query:
                search_condition = (
                    ReadModelDeal.client_name.ilike(f"%{query}%")
                    | ReadModelDeal.invoice_info.ilike(f"%{query}%")
                    | ReadModelDeal.seller.ilike(f"%{query}%")
                )
                base_query = base_query.where(search_condition)

            # Add filters
            if filters:
                if "period_year" in filters:
                    base_query = base_query.where(
                        ReadModelDeal.period_year == filters["period_year"]
                    )
                if "period_month" in filters:
                    base_query = base_query.where(
                        ReadModelDeal.period_month == filters["period_month"]
                    )
                if "client_name" in filters:
                    base_query = base_query.where(
                        ReadModelDeal.client_name.ilike(f"%{filters['client_name']}%")
                    )

            # Count total
            count_query = select(func.count()).select_from(base_query.subquery())
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar()

            # Get paginated results
            paginated_query = (
                base_query.order_by(ReadModelDeal.created_at.desc()).limit(limit).offset(offset)
            )

            result = await self.session.execute(paginated_query)
            deal_models = result.scalars().all()

            # Convert to simple dicts for API response
            deals = []
            for model in deal_models:
                deal_dict = {
                    "id": str(model.id),
                    "deal_key": model.deal_key,
                    "client_name": model.client_name,
                    "invoice_info": model.invoice_info,
                    "period_month": model.period_month,
                    "period_year": model.period_year,
                    "is_shipped": model.is_shipped,
                    "is_paid": model.is_paid,
                    "total_revenue_amount": float(model.total_revenue_amount)
                    if model.total_revenue_amount
                    else None,
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                }
                deals.append(deal_dict)

            return {
                "deals": deals,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": total_count > offset + limit,
            }

        except Exception as e:
            logger.error(f"Failed to search deals: {e}")
            raise
