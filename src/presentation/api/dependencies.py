"""
Dependency injection for FastAPI.

Contains dependencies for injecting services into API endpoints.
"""

from __future__ import annotations

# Mock implementations for now - these would be replaced with real services
# when database connections are established


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
                "saller": "Продавец 1",
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
                "saller": "Продавец 2",
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

        # Apply basic filtering
        filtered_deals = mock_deals
        if filters.get("client_name"):
            filtered_deals = [
                d
                for d in filtered_deals
                if filters["client_name"].lower() in d["client_name"].lower()
            ]

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
            "saller": "Продавец 1",
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


# Dependency providers
async def get_deal_service() -> MockDealService:
    """Get deal service dependency."""
    return MockDealService()


async def get_sync_service() -> MockSyncService:
    """Get sync service dependency."""
    return MockSyncService()


async def get_health_service() -> MockHealthService:
    """Get health service dependency."""
    return MockHealthService()
