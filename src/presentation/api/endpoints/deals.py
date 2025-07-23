"""
Deal management endpoints.

Provides CRUD operations and analytics for deals with filtering and pagination.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..auth.security import require_viewer
from ..dependencies import MockDealService, get_deal_service
from ..models.common import PaginationParams, PaginationResponse
from ..models.deals import (
    DealFilters,
    DealResponse,
    DealStatsResponse,
    DealSummary,
)

deals_router = APIRouter()


@deals_router.get("/", response_model=PaginationResponse[DealSummary])
async def list_deals(
    pagination: PaginationParams = Depends(),
    filters: DealFilters = Depends(),
    current_user=Depends(require_viewer),
    deal_service: MockDealService = Depends(get_deal_service),
) -> PaginationResponse[DealSummary]:
    """
    List deals with filtering and pagination.

    Args:
        pagination: Pagination parameters
        filters: Filter parameters
        current_user: Current authenticated user

    Returns:
        PaginationResponse[DealSummary]: Paginated list of deals
    """
    logger.info(f"User {current_user.username} requested deals list")

    # Get deals through service layer
    filters_dict = filters.model_dump(exclude_none=True)
    result = await deal_service.get_deals_paginated(
        page=pagination.page, limit=pagination.limit, filters=filters_dict
    )

    # Convert to DealSummary objects
    deal_summaries = [DealSummary(**item) for item in result["items"]]

    return PaginationResponse(
        items=deal_summaries,
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        pages=result["pages"],
    )


@deals_router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: str,
    current_user=Depends(require_viewer),
    deal_service: MockDealService = Depends(get_deal_service),
) -> DealResponse:
    """
    Get detailed deal information.

    Args:
        deal_id: Deal ID
        current_user: Current authenticated user

    Returns:
        DealResponse: Detailed deal information
    """
    logger.info(f"User {current_user.username} requested deal {deal_id}")

    # Get deal through service layer
    deal_data = await deal_service.get_deal_by_id(deal_id)
    if not deal_data:
        raise HTTPException(status_code=404, detail="Deal not found")

    return DealResponse(**deal_data)


@deals_router.get("/{deal_id}/history")
async def get_deal_history(deal_id: str, current_user=Depends(require_viewer)) -> list[dict]:
    """
    Get deal change history.

    Args:
        deal_id: Deal ID
        current_user: Current authenticated user

    Returns:
        list[dict]: Deal change history
    """
    logger.info(f"User {current_user.username} requested history for deal {deal_id}")

    # TODO: Get deal history from event store - this needs integration with real event store
    return [
        {
            "event_id": "event-1",
            "event_type": "DealCreated",
            "timestamp": datetime(2024, 1, 15, 10, 0, 0).isoformat(),
            "user": "system",
            "changes": {"action": "created"},
        },
        {
            "event_id": "event-2",
            "event_type": "DealUpdated",
            "timestamp": datetime(2024, 1, 16, 14, 30, 0).isoformat(),
            "user": "system",
            "changes": {"field": "is_shipped", "old_value": False, "new_value": True},
        },
    ]


@deals_router.get("/stats/summary", response_model=DealStatsResponse)
async def get_deals_stats(
    period_month: str | None = Query(None, description="Filter by month"),
    period_year: str | None = Query(None, description="Filter by year"),
    current_user=Depends(require_viewer),
) -> DealStatsResponse:
    """
    Get deal statistics and analytics.

    Args:
        period_month: Filter by month
        period_year: Filter by year
        current_user: Current authenticated user

    Returns:
        DealStatsResponse: Deal statistics
    """
    logger.info(f"User {current_user.username} requested deal statistics")

    # TODO: Calculate real statistics from database - this needs integration with real services
    return DealStatsResponse(
        total_deals=150,
        total_revenue=Decimal("5000000.00"),
        total_margin=Decimal("1000000.00"),
        shipped_deals=120,
        paid_deals=100,
        avg_revenue=Decimal("33333.33"),
        top_clients=[
            {"client_name": "ООО Компания 1", "revenue": Decimal("500000.00")},
            {"client_name": "ООО Компания 2", "revenue": Decimal("400000.00")},
            {"client_name": "ООО Компания 3", "revenue": Decimal("300000.00")},
        ],
        revenue_by_month=[
            {"month": "2024-01", "revenue": Decimal("1500000.00")},
            {"month": "2024-02", "revenue": Decimal("1800000.00")},
            {"month": "2024-03", "revenue": Decimal("1700000.00")},
        ],
    )
