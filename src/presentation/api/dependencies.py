"""
Dependency injection for FastAPI.

Contains dependencies for injecting services into API endpoints.
Supports both mock services (for testing) and real services (for production).
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.change_detector import ChangeDetectorService
from src.application.excel_parser import ExcelParserService
from src.application.sync_orchestrator import SyncOrchestratorService
from src.infrastructure.database.connection import get_database_manager, get_database_session
from src.infrastructure.database.event_store import EventStoreImplementation
from src.infrastructure.database.repositories import (
    DealRepositoryImplementation,
    SyncSessionRepositoryImplementation,
)

from .services import RealDealService, RealHealthService, RealSyncService

# Mock implementations kept for backward compatibility and testing


class MockDealService:
    """Mock deal service for API endpoints."""

    async def get_deals_paginated(self, page: int, limit: int, filters: dict) -> dict:
        """Get paginated deals with filters."""
        # This is mock data - in real implementation would query database
        from datetime import datetime
        from decimal import Decimal

        mock_deals = [
            {
                "id": "deal-1",
                "deal_key": "CLIENT1_INV001_2024-01-15_SELLER1",
                "client_name": "ООО Компания 1",
                "seller": "Продавец 1",
                "invoice_number": "INV001",
                "invoice_date": datetime(2024, 1, 15).date(),
                "revenue": Decimal("100000.00"),
                "margin": Decimal("20000.00"),
                "is_shipped": True,
                "is_paid": True,
                "items_count": 5,
                "updated_at": datetime(2024, 1, 15, 10, 0, 0),
            },
            {
                "id": "deal-2",
                "deal_key": "CLIENT2_INV002_2024-01-16_SELLER2",
                "client_name": "ООО Компания 2",
                "seller": "Продавец 2",
                "invoice_number": "INV002",
                "invoice_date": datetime(2024, 1, 16).date(),
                "revenue": Decimal("75000.00"),
                "margin": Decimal("15000.00"),
                "is_shipped": False,
                "is_paid": False,
                "items_count": 3,
                "updated_at": datetime(2024, 1, 16, 14, 30, 0),
            },
        ]

        # Apply filtering
        filtered_deals = mock_deals

        # Client name filter
        if filters.get("client_name"):
            filtered_deals = [
                d
                for d in filtered_deals
                if filters["client_name"].lower() in d["client_name"].lower()
            ]

        # Seller filter
        if filters.get("seller"):
            filtered_deals = [
                d
                for d in filtered_deals
                if filters["seller"].lower() in d["seller"].lower()
            ]

        # Boolean filters
        if filters.get("is_shipped") is not None:
            is_shipped_filter = str(filters["is_shipped"]).lower() == "true"
            filtered_deals = [d for d in filtered_deals if d["is_shipped"] == is_shipped_filter]

        if filters.get("is_paid") is not None:
            is_paid_filter = str(filters["is_paid"]).lower() == "true"
            filtered_deals = [d for d in filtered_deals if d["is_paid"] == is_paid_filter]

        # Pagination
        total = len(filtered_deals)
        start = (page - 1) * limit
        end = start + limit
        items = filtered_deals[start:end]

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    async def get_deal_by_id(self, deal_id: str) -> dict | None:
        """Get deal by ID."""
        from datetime import datetime
        from decimal import Decimal

        return {
            "id": deal_id,
            "deal_key": "CLIENT1_INV001_2024-01-15_SELLER1",
            "client_name": "ООО Компания 1",
            "seller": "Продавец 1",
            "invoice_number": "INV001",
            "invoice_date": datetime(2024, 1, 15).date(),
            "upd_number": "UPD001",
            "upd_date": datetime(2024, 1, 16).date(),
            "revenue": Decimal("100000.00"),
            "margin": Decimal("20000.00"),
            "cost": Decimal("80000.00"),
            "is_shipped": True,
            "is_paid": True,
            "period_month": "01",
            "period_year": "2024",
            "created_at": datetime(2024, 1, 15, 10, 0, 0),
            "updated_at": datetime(2024, 1, 15, 10, 0, 0),
            "items": [],
        }


class MockSyncService:
    """Mock sync service for API endpoints."""

    async def get_sessions_paginated(self, page: int, limit: int, filters: dict) -> dict:
        """Get paginated sync sessions."""
        from datetime import datetime

        mock_sessions = [
            {
                "id": "session-1",
                "session_type": "incremental",
                "status": "completed",
                "started_at": datetime(2024, 1, 15, 3, 0, 0),
                "finished_at": datetime(2024, 1, 15, 3, 5, 30),
                "duration_seconds": 330.0,
                "total_deals_processed": 25,
                "success": True,
                "error_message": None,
            },
            {
                "id": "session-2",
                "session_type": "full",
                "status": "failed",
                "started_at": datetime(2024, 1, 14, 3, 0, 0),
                "finished_at": datetime(2024, 1, 14, 3, 2, 15),
                "duration_seconds": 135.0,
                "total_deals_processed": 0,
                "success": False,
                "error_message": "File not found: data.xlsx",
            },
        ]

        # Apply filtering
        filtered_sessions = mock_sessions
        if filters.get("status"):
            filtered_sessions = [s for s in filtered_sessions if s["status"] == filters["status"]]

        # Pagination
        total = len(filtered_sessions)
        start = (page - 1) * limit
        end = start + limit
        items = filtered_sessions[start:end]

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    async def get_session_by_id(self, session_id: str) -> dict | None:
        """Get sync session by ID."""
        from datetime import datetime

        return {
            "id": session_id,
            "session_type": "incremental",
            "status": "completed",
            "started_at": datetime(2024, 1, 15, 3, 0, 0),
            "finished_at": datetime(2024, 1, 15, 3, 5, 30),
            "created_at": datetime(2024, 1, 15, 2, 55, 0),  # Добавляем created_at
            "duration_seconds": 330.0,
            "total_deals_processed": 25,
            "success": True,
            "error_message": None,
            "file_path": "test_data.xlsx",
            "file_size": 2048,
            "file_hash": "abc123def456",
        }

    async def create_sync_session(self, file_path: str, session_type: str = "incremental", force: bool = False) -> dict:
        """Create new sync session."""
        import uuid
        from datetime import datetime

        session_id = str(uuid.uuid4())
        return {
            "id": session_id,
            "session_type": session_type,
            "status": "running",  # Исправлено: running вместо pending
            "started_at": datetime.now(),
            "finished_at": None,
            "created_at": datetime.now(),
            "duration_seconds": None,
            "success": False,  # Исправлено: boolean вместо None
            "error_message": None,
            "file_path": file_path,
            "created_by": None,
        }


class MockHealthService:
    """Mock health service for system monitoring."""

    async def get_database_status(self) -> dict:
        """Check database connection status."""
        # TODO: Implement real database connection check
        return {"status": "unknown", "details": "Database check not implemented"}

    async def get_system_metrics(self) -> dict:
        """Get system metrics."""
        # TODO: Implement real metrics collection
        return {
            "requests_total": 0,
            "requests_duration_seconds": 0.0,
            "database_connections": 0,
            "active_sessions": 0,
        }


# Mock dependency providers (for testing and development)
async def get_mock_deal_service() -> MockDealService:
    """Get mock deal service dependency."""
    return MockDealService()


async def get_mock_sync_service() -> MockSyncService:
    """Get mock sync service dependency."""
    return MockSyncService()


async def get_mock_health_service() -> MockHealthService:
    """Get mock health service dependency."""
    return MockHealthService()


# Real dependency providers (for production)
async def get_real_deal_service(
    db: AsyncSession = Depends(get_database_session),
) -> RealDealService:
    """Get real deal service dependency with database connection."""
    deal_repository = DealRepositoryImplementation(db)
    return RealDealService(deal_repository)


async def get_real_sync_service(
    db: AsyncSession = Depends(get_database_session),
) -> RealSyncService:
    """Get real sync service dependency with orchestrator."""
    # Create repositories
    deal_repository = DealRepositoryImplementation(db)
    sync_session_repository = SyncSessionRepositoryImplementation(db)
    event_store = EventStoreImplementation(db)

    # Create application services
    excel_parser = ExcelParserService()
    change_detector = ChangeDetectorService(deal_repository)

    # Create orchestrator
    sync_orchestrator = SyncOrchestratorService(
        excel_parser=excel_parser,
        change_detector=change_detector,
        event_store=event_store,
        sync_session_repository=sync_session_repository,
    )

    return RealSyncService(
        sync_orchestrator=sync_orchestrator,
        sync_session_repository=sync_session_repository,
    )


async def get_real_health_service() -> RealHealthService:
    """Get real health service dependency with database manager."""
    db_manager = await get_database_manager()
    return RealHealthService(db_manager)


# Current active providers (switch between mock and real)
# Change these to switch between mock and real services globally
async def get_deal_service(
    real_service: RealDealService = Depends(get_real_deal_service),
) -> RealDealService:
    """Get active deal service dependency."""
    return real_service


async def get_sync_service(
    real_service: RealSyncService = Depends(get_real_sync_service),
) -> RealSyncService:
    """Get active sync service dependency."""
    return real_service


async def get_health_service(
    real_service: RealHealthService = Depends(get_real_health_service),
) -> RealHealthService:
    """Get active health service dependency."""
    return real_service
