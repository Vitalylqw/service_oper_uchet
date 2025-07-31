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
from ..dependencies import get_deal_service, get_stats_service
from ..models.common import PaginationParams, PaginationResponse
from ..models.deals import (
    DealFilters,
    DealResponse,
    DealStatsResponse,
    DealSummary,
)
from ..services import RealDealService, StatsService

deals_router = APIRouter()


@deals_router.get("/", response_model=PaginationResponse[DealSummary])
async def list_deals(
    pagination: PaginationParams = Depends(),
    filters: DealFilters = Depends(),
    current_user=Depends(require_viewer),
    deal_service: RealDealService = Depends(get_deal_service),
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


@deals_router.get("/stats", response_model=DealStatsResponse)
async def get_deals_stats(
    period_month: str | None = Query(None, description="Filter by month"),
    period_year: str | None = Query(None, description="Filter by year"),
    current_user=Depends(require_viewer),
    stats_service: StatsService = Depends(get_stats_service),
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

    stats = await stats_service.get_deal_stats(period_month, period_year)

    return DealStatsResponse(
        total_deals=stats["total_deals"],
        total_revenue=Decimal(str(stats["total_revenue"])),
        total_margin=Decimal(str(stats["total_margin"])),
        shipped_deals=stats["shipped_deals"],
        paid_deals=stats["paid_deals"],
        unpaid_deals=stats["unpaid_deals"],
        unshipped_deals=stats["unshipped_deals"],
        avg_revenue=Decimal(str(stats["avg_revenue"])),
        avg_profitability=Decimal(str(stats["avg_profitability"])), 
        top_clients=[],  # TODO: implement
        revenue_by_month=[],  # TODO: implement
    )


@deals_router.get("/stats/summary", response_model=DealStatsResponse)
async def get_deals_stats_summary(
    period_month: str | None = Query(None, description="Filter by month"),
    period_year: str | None = Query(None, description="Filter by year"),
    current_user=Depends(require_viewer),
    stats_service: StatsService = Depends(get_stats_service),
) -> DealStatsResponse:
    """Alias to keep backward compatibility with older clients/tests."""
    return await get_deals_stats(period_month, period_year, current_user, stats_service)


@deals_router.get("/debug-stats")
async def debug_stats(current_user=Depends(require_viewer)):
    """Debug endpoint to see what's wrong with stats."""
    logger.info(f"User {current_user.username} requested debug stats")

    return {
        "status": "debug_mode",
        "message": "Stats endpoint working in debug mode",
        "timestamp": datetime.now().isoformat(),
        "user": current_user.username
    }


@deals_router.get("/test-new-code")
async def test_new_code():
    """Test endpoint to verify server restart."""
    return {"message": "NEW CODE DEPLOYED!", "timestamp": "2025-07-26T22:50:00"}


@deals_router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: str,
    current_user=Depends(require_viewer),
    deal_service: RealDealService = Depends(get_deal_service),
) -> DealResponse:
    """
    Get detailed deal information.

    Args:
        deal_id: Deal ID
        current_user: Current authenticated user

    Returns:
        DealResponse: Detailed deal information
    """
    try:
        logger.info(f"User {current_user.username} requested deal {deal_id}")
        logger.debug(f"Deal service type: {type(deal_service)}")

        # Get deal through service layer
        logger.debug("Calling deal_service.get_deal_by_id...")
        deal_data = await deal_service.get_deal_by_id(deal_id)
        logger.debug(f"Service returned: {deal_data is not None}")

        if not deal_data:
            logger.debug(f"Deal not found: {deal_id}")
            raise HTTPException(status_code=404, detail="Deal not found")

        logger.debug("Creating DealResponse...")
        response = DealResponse(**deal_data)
        logger.debug("DealResponse created successfully")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_deal endpoint: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


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
