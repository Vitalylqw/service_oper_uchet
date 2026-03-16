"""
Sync Orchestrator Service.

Coordinates the complete synchronization process including Excel parsing,
change detection, event creation, and database updates.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from domain.interfaces import EventStore, SyncSessionRepository
from domain.models import SyncSession, SyncType
from infrastructure.workers.read_model_builder import ReadModelBuilder

from ..change_detector import ChangeDetectorService
from ..excel_parser import ExcelParserService
from .models import SyncConfiguration, SyncResult, SyncSummary


class SyncOrchestratorService:
    """
    Main orchestrator for synchronization operations.

    Coordinates all steps of the sync process:
    1. Session creation and management
    2. Excel file parsing
    3. Change detection against database
    4. Event creation and storage
    5. Read model updates
    6. Session completion and reporting
    """

    def __init__(
        self,
        excel_parser: ExcelParserService,
        change_detector: ChangeDetectorService,
        event_store: EventStore,
        sync_session_repository: SyncSessionRepository,
        read_model_builder: ReadModelBuilder | None = None,
    ) -> None:
        """Initialize orchestrator with required services."""
        self.excel_parser = excel_parser
        self.change_detector = change_detector
        self.event_store = event_store
        self.sync_session_repository = sync_session_repository
        self.read_model_builder = read_model_builder

    async def execute_sync(self, file_path: str, config: SyncConfiguration) -> SyncResult:
        """
        Execute complete synchronization process.

        Args:
            file_path: Path to Excel file to process
            config: Synchronization configuration

        Returns:
            SyncResult with complete operation details

        Raises:
            Exception: If sync fails and rollback_on_failure is True
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())

        logger.info(f"Starting sync session {session_id} ({config.sync_type})")
        logger.info(f"Processing file: {file_path}")

        # Create sync session
        sync_session = await self._create_sync_session(session_id, file_path, config)

        # Initialize result
        result = SyncResult(
            sync_session_id=session_id,
            sync_type=config.sync_type,
            summary=SyncSummary(
                started_at=datetime.now(),
                file_path=file_path,
                file_hash="",  # Will be set during parsing
            ),
        )

        try:
            # Phase 1: Parse Excel file
            logger.info("📋 Phase 1: Parsing Excel file...")
            parse_start = time.time()

            result.parse_result = await self.excel_parser.parse_file(file_path, sync_session)
            result.summary.file_hash = result.parse_result.file_hash
            result.summary.file_size_bytes = result.parse_result.file_size
            result.summary.total_deals_processed = result.parse_result.total_deals
            result.summary.total_items_processed = result.parse_result.total_items
            result.summary.parsing_duration_seconds = time.time() - parse_start

            if result.parse_result.has_errors:
                result.add_warning(
                    f"Parsing completed with {len(result.parse_result.stats.errors)} errors"
                )

            logger.info(
                f"✅ Parsing completed: {result.parse_result.total_deals} deals, "
                f"{result.parse_result.total_items} items in "
                f"{result.summary.parsing_duration_seconds:.2f}s"
            )

            # Phase 2: Detect changes (unified for full/partial by provided periods)
            logger.info("🔍 Phase 2: Detecting changes...")
            change_start = time.time()

            # For new simplified logic, we don't use period months anymore
            # Change detection will use the target periods from config if partial sync
            result.change_detection_result = await self.change_detector.detect_changes(
                result.parse_result.deals, sync_period_months=0  # Not used in new logic
            )

            result.summary.insertions_count = result.change_detection_result.insertion_count
            result.summary.updates_count = result.change_detection_result.update_count
            result.summary.deletions_count = result.change_detection_result.deletion_count
            result.summary.change_detection_duration_seconds = time.time() - change_start

            logger.info(
                f"✅ Change detection completed: {result.change_detection_result.total_changes} changes "
                f"in {result.summary.change_detection_duration_seconds:.2f}s"
            )

            # Phase 3: Apply changes to database
            logger.info("💾 Phase 3: Applying changes to database...")
            db_start = time.time()

            await self._apply_changes_to_database(result, config)
            result.summary.database_update_duration_seconds = time.time() - db_start

            logger.info(
                f"✅ Database update completed in "
                f"{result.summary.database_update_duration_seconds:.2f}s"
            )

            # Complete session successfully
            await self._complete_sync_session(sync_session, True)
            result.summary.success = True

            # Final timing
            result.summary.finished_at = datetime.now()
            result.summary.duration_seconds = time.time() - start_time

            logger.info(
                f"🎉 Sync session {session_id} completed successfully in "
                f"{result.summary.duration_seconds:.2f}s"
            )

            return result

        except Exception as e:
            error_msg = f"Sync session {session_id} failed: {str(e)}"
            logger.error(error_msg)

            result.add_error(error_msg)
            result.summary.finished_at = datetime.now()
            result.summary.duration_seconds = time.time() - start_time

            # Complete session with failure
            await self._complete_sync_session(sync_session, False, str(e))

            if config.rollback_on_failure:
                logger.warning("Rolling back changes due to failure")
                await self._rollback_sync_changes(session_id, result)

            if not config.continue_on_errors:
                raise

            return result

    async def _create_sync_session(
        self, session_id: str, file_path: str, config: SyncConfiguration
    ) -> SyncSession:
        """Create and save new sync session."""
        try:
            # Check for running sessions
            running_session = await self.sync_session_repository.get_running_session()
            if running_session:
                raise RuntimeError(f"Another sync session is already running: {running_session.id}")

            # Create new session
            sync_type = SyncType.FULL if config.is_full_sync() else SyncType.INCREMENTAL
            sync_session = SyncSession(sync_type=sync_type)
            sync_session.id = uuid.UUID(session_id)
            sync_session.source_file_path = file_path

            # Compute file metadata to satisfy NOT NULL DB constraints
            try:
                import hashlib as _hashlib
                from pathlib import Path as _Path

                _p = _Path(file_path)
                if _p.exists() and _p.is_file():
                    sync_session.source_file_size = _p.stat().st_size
                    sync_session.source_file_hash = _hashlib.md5(_p.read_bytes()).hexdigest()
                else:
                    # Fallback placeholders to avoid DB nulls
                    sync_session.source_file_size = 0
                    sync_session.source_file_hash = "unknown"
            except Exception as _e:
                logger.warning(f"Failed to compute file metadata for {file_path}: {_e}")
                sync_session.source_file_size = 0
                sync_session.source_file_hash = "unknown"

            sync_session.start()

            # Save to database
            await self.sync_session_repository.save(sync_session)

            logger.debug(f"Created sync session {session_id}")
            return sync_session

        except Exception as e:
            logger.error(f"Failed to create sync session: {e}")
            raise

    async def _complete_sync_session(
        self, sync_session: SyncSession, success: bool, error_message: str | None = None
    ) -> None:
        """Complete sync session with result."""
        try:
            if success:
                sync_session.complete_success()
            else:
                sync_session.complete_failed(error_message or "Unknown error")

            await self.sync_session_repository.save(sync_session)
            logger.debug(f"Completed sync session {sync_session.id} (success: {success})")

        except Exception as e:
            logger.error(f"Failed to complete sync session: {e}")
            # Don't re-raise - session completion failure shouldn't fail the whole sync

    async def _rollback_sync_changes(self, session_id: str, result: SyncResult) -> None:
        """Rollback database changes made during a failed sync session.

        Performs best-effort rollback:
        1. Deletes events appended to the event store during this session.
        2. For INSERT events, removes the corresponding read model records.
        3. Logs warnings for UPDATE/DELETE changes that cannot be fully reversed
           without prior state (a full read model rebuild would be needed).

        Args:
            session_id: ID of the failed sync session.
            result: SyncResult containing the list of events that were created.
        """
        try:
            # Step 1: Remove events from event store
            deleted_count = await self.event_store.delete_events_by_session_id(session_id)
            logger.info(f"Rollback: deleted {deleted_count} events for session {session_id}")

            # Step 2: Reverse read model changes for INSERT events
            if result.events_created and self.read_model_builder:
                insert_aggregate_ids: list[Any] = []
                has_non_insert = False

                for event in result.events_created:
                    change_type = (event.get("metadata") or {}).get("change_type")
                    if change_type == "INSERT":
                        aggregate_id = event.get("aggregate_id")
                        if aggregate_id is not None:
                            insert_aggregate_ids.append(aggregate_id)
                    elif change_type in ("UPDATE", "DELETE"):
                        has_non_insert = True

                if insert_aggregate_ids:
                    from sqlalchemy import delete as sa_delete
                    from infrastructure.database.models import ReadModelDeal, ReadModelPosition

                    await self.read_model_builder.session.execute(
                        sa_delete(ReadModelPosition).where(
                            ReadModelPosition.deal_id.in_(insert_aggregate_ids)
                        )
                    )
                    await self.read_model_builder.session.execute(
                        sa_delete(ReadModelDeal).where(
                            ReadModelDeal.id.in_(insert_aggregate_ids)
                        )
                    )
                    await self.read_model_builder.session.flush()
                    logger.info(
                        f"Rollback: removed {len(insert_aggregate_ids)} inserted deal(s) "
                        "from read model"
                    )

                if has_non_insert:
                    logger.warning(
                        "Rollback: UPDATE/DELETE read model changes cannot be automatically "
                        "reversed. Consider triggering a full read model rebuild."
                    )
            elif result.events_created:
                logger.warning(
                    "Rollback: read_model_builder not available; "
                    "read model may be inconsistent after rollback"
                )

        except Exception as rollback_err:
            logger.error(f"Rollback failed for session {session_id}: {rollback_err}")

    async def _apply_changes_to_database(
        self, result: SyncResult, config: SyncConfiguration
    ) -> None:
        """Apply detected changes to database through events."""
        try:
            if not config.create_events:
                logger.info("Event creation disabled, skipping database updates")
                return

            events_to_create = []

            # Create events for detected changes only (unified)
            if result.change_detection_result:
                events_to_create = await self._create_incremental_sync_events(result)

            if events_to_create:
                logger.info(f"Creating {len(events_to_create)} events in event store")
                await self.event_store.append_events(events_to_create)
                result.events_created = events_to_create

            if config.update_read_models:
                if self.read_model_builder:
                    logger.info("Updating read models from events...")
                    # Обрабатываем все события одной большой порцией,
                    # чтобы не возвращаться к тем же событиям повторно
                    total_events = await self.read_model_builder.process_latest_events(
                        limit=1_000_000,  # оценочно должно покрыть nightly-объём
                        auto_commit=True,
                    )
                    logger.info(f"✅ Read models updated for {total_events} events")
                else:
                    logger.warning("Read model builder not configured, skipping read model updates")

        except Exception as e:
            logger.error(f"Failed to apply changes to database: {e}")
            raise

    async def _create_full_sync_events(self, result: SyncResult) -> list[dict[str, Any]]:
        """Create events for full synchronization."""
        events = []

        if not result.parse_result:
            return events

        for deal in result.parse_result.deals:
            # Create DealCreated event
            deal_event = {
                "aggregate_id": deal.id,
                "event_type": "DealCreated",
                "event_data": {
                    "deal_id": str(deal.id),
                    "deal_key": deal.deal_key,
                    "client_name": deal.client_name,
                    "invoice_info": deal.invoice_info,
                    "invoice_number": deal.invoice_number,
                    "invoice_date": deal.invoice_date,
                    "period": {
                        "month": deal.period.month,
                        "year": deal.period.year,
                        "full_name": deal.period.full_name,
                    },
                    "is_shipped": deal.is_shipped.value if deal.is_shipped else None,
                    "is_paid": deal.is_paid.value if deal.is_paid else None,
                    "upd_number": deal.upd_number,
                    "seller": deal.seller,
                    "totals": {
                        "revenue": str(deal.total_revenue.amount)
                        if deal.total_revenue
                        else None,
                        "margin": str(deal.total_margin.amount)
                        if deal.total_margin
                        else None,
                        "cost": str(deal.total_cost.amount)
                        if deal.total_cost
                        else None,
                        "kickback": str(deal.kickback_amount.amount)
                        if deal.kickback_amount
                        else None,
                    },
                },
                "metadata": {
                    "sync_session_id": result.sync_session_id,
                    "sync_type": result.sync_type,
                    "source": "excel_sync",
                },
            }
            events.append(deal_event)

            # Create DealItemAdded events for each item
            for item in deal.items:
                item_event = {
                    "aggregate_id": deal.id,
                    "event_type": "DealItemAdded",
                    "event_data": {
                        "deal_id": str(deal.id),
                        "item_id": str(item.id),
                        "product_name": item.product_name,
                        "supplier_name": item.supplier_name,
                        "pickup_date": item.pickup_date,
                        "quantity": str(item.quantity) if item.quantity else None,
                        "position_number": item.position_number,  # Add position_number to event data
                        "prices": {
                            "purchase": str(item.purchase_price.amount)
                            if item.purchase_price
                            else None,
                            "sale": str(item.sale_price.amount)
                            if item.sale_price
                            else None,
                            "revenue": str(item.revenue.amount)
                            if item.revenue
                            else None,
                            "margin": str(item.margin.amount)
                            if item.margin
                            else None,
                            "cost": str(item.cost.amount)
                            if item.cost
                            else None,
                        },
                    },
                    "metadata": {
                        "sync_session_id": result.sync_session_id,
                        "sync_type": result.sync_type,
                        "source": "excel_sync",
                    },
                }
                events.append(item_event)

        logger.debug(f"Created {len(events)} events for full sync")
        return events

    def _build_deal_with_positions_event(
        self,
        deal: Any,
        change_type: str,
        sync_session_id: str,
        sync_type: str,
    ) -> dict[str, Any]:
        """Build DealWithPositionsCreated event for atomic deal processing.

        Args:
            deal: Deal domain object with items.
            change_type: INSERT or UPDATE.
            sync_session_id: Current sync session identifier.
            sync_type: Sync type (full/incremental).

        Returns:
            Event dict ready for event_store.append_events().
        """
        items_data = []
        for item in deal.items:
            items_data.append({
                "item_id": str(item.id),
                "product_name": item.product_name,
                "supplier_name": item.supplier_name,
                "pickup_date": item.pickup_date,
                "quantity": str(item.quantity) if item.quantity else None,
                "position_number": item.position_number,
                "prices": {
                    "purchase": (
                        str(item.purchase_price.amount)
                        if item.purchase_price else None
                    ),
                    "sale": (
                        str(item.sale_price.amount)
                        if item.sale_price else None
                    ),
                    "revenue": (
                        str(item.revenue.amount) if item.revenue else None
                    ),
                    "margin": (
                        str(item.margin.amount) if item.margin else None
                    ),
                    "cost": (
                        str(item.cost.amount) if item.cost else None
                    ),
                },
            })

        return {
            "aggregate_id": deal.id,
            "event_type": "DealWithPositionsCreated",
            "event_data": {
                "deal": {
                    "deal_id": str(deal.id),
                    "deal_key": deal.deal_key,
                    "client_name": deal.client_name,
                    "invoice_info": deal.invoice_info,
                    "invoice_number": deal.invoice_number,
                    "invoice_date": deal.invoice_date,
                    "period": {
                        "month": deal.period.month,
                        "year": deal.period.year,
                        "full_name": deal.period.full_name,
                    },
                    "is_shipped": (
                        deal.is_shipped.value if deal.is_shipped else None
                    ),
                    "is_paid": (
                        deal.is_paid.value if deal.is_paid else None
                    ),
                    "upd_number": deal.upd_number,
                    "seller": deal.seller,
                    "totals": {
                        "revenue": (
                            str(deal.total_revenue.amount)
                            if deal.total_revenue else None
                        ),
                        "margin": (
                            str(deal.total_margin.amount)
                            if deal.total_margin else None
                        ),
                        "cost": (
                            str(deal.total_cost.amount)
                            if deal.total_cost else None
                        ),
                        "kickback": (
                            str(deal.kickback_amount.amount)
                            if deal.kickback_amount else None
                        ),
                    },
                },
                "items": items_data,
            },
            "metadata": {
                "sync_session_id": sync_session_id,
                "sync_type": sync_type,
                "change_type": change_type,
                "source": "excel_sync",
            },
        }

    async def _create_incremental_sync_events(
        self, result: SyncResult
    ) -> list[dict[str, Any]]:
        """Create events for incremental synchronization.

        Uses atomic deal processing:
        - deal INSERT/UPDATE -> DealWithPositionsCreated (full deal rewrite)
        - deal DELETE -> DealDeleted
        - deal_item changes are covered by deal-level events (skipped)
        """
        events: list[dict[str, Any]] = []

        if not result.change_detection_result:
            return events

        for change in result.change_detection_result.insertions:
            if change.entity_type.value == "deal" and change.new_entity:
                events.append(self._build_deal_with_positions_event(
                    deal=change.new_entity,
                    change_type="INSERT",
                    sync_session_id=result.sync_session_id,
                    sync_type=result.sync_type,
                ))

        for change in result.change_detection_result.updates:
            if change.entity_type.value == "deal" and change.new_entity:
                events.append(self._build_deal_with_positions_event(
                    deal=change.new_entity,
                    change_type="UPDATE",
                    sync_session_id=result.sync_session_id,
                    sync_type=result.sync_type,
                ))

        for change in result.change_detection_result.deletions:
            if change.entity_type.value == "deal" and change.old_entity:
                deal = change.old_entity
                events.append({
                    "aggregate_id": deal.id,
                    "event_type": "DealDeleted",
                    "event_data": {
                        "deal_id": str(deal.id),
                        "deal_key": deal.deal_key,
                        "deletion_reason": "not_in_excel",
                    },
                    "metadata": {
                        "sync_session_id": result.sync_session_id,
                        "sync_type": result.sync_type,
                        "change_type": "DELETE",
                        "source": "excel_sync",
                    },
                })

        logger.debug(f"Created {len(events)} events for incremental sync")
        return events

    async def get_sync_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get history of recent sync sessions."""
        try:
            sessions = await self.sync_session_repository.get_latest_sessions(limit)

            history = []
            for session in sessions:
                session_dict = {
                    "id": str(session.id),
                    "sync_type": session.sync_type.value,
                    "status": session.status.value,
                    "file_path": session.source_file_path,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "finished_at": session.finished_at.isoformat() if session.finished_at else None,
                    "duration_seconds": session.duration_seconds,
                    "notes": session.notes,  # Changed from error_message to notes
                }
                history.append(session_dict)

            return history

        except Exception as e:
            logger.error(f"Failed to get sync history: {e}")
            return []

    async def get_running_session(self) -> dict[str, Any] | None:
        """Get currently running sync session if any."""
        try:
            session = await self.sync_session_repository.get_running_session()
            if not session:
                return None

            return {
                "id": str(session.id),
                "sync_type": session.sync_type.value,
                "status": session.status.value,
                "file_path": session.source_file_path,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "duration_seconds": session.duration_seconds,
            }

        except Exception as e:
            logger.error(f"Failed to get running session: {e}")
            return None
