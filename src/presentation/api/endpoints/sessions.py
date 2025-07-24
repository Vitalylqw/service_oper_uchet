"""
Sync session management endpoints.

Provides CRUD operations and monitoring for synchronization sessions.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from loguru import logger

from ..auth.security import require_analyst, require_viewer
from ..dependencies import get_sync_service
from ..models.common import PaginationParams, PaginationResponse
from ..models.sessions import (
    SyncSessionCreateRequest,
    SyncSessionFilters,
    SyncSessionResponse,
    SyncSessionSummary,
    SyncStatsResponse,
)
from ..services import RealSyncService

sessions_router = APIRouter()


@sessions_router.get("/", response_model=PaginationResponse[SyncSessionSummary])
async def list_sync_sessions(
    pagination: PaginationParams = Depends(),
    filters: SyncSessionFilters = Depends(),
    current_user=Depends(require_viewer),
    sync_service: RealSyncService = Depends(get_sync_service),
) -> PaginationResponse[SyncSessionSummary]:
    """
    List sync sessions with filtering and pagination.

    Args:
        pagination: Pagination parameters
        filters: Filter parameters
        current_user: Current authenticated user

    Returns:
        PaginationResponse[SyncSessionSummary]: Paginated list of sync sessions
    """
    logger.info(f"User {current_user.username} requested sync sessions list")

    # Get sessions through real service layer
    filters_dict = filters.model_dump(exclude_none=True)
    result = await sync_service.get_sessions_paginated(
        page=pagination.page, limit=pagination.limit, filters=filters_dict
    )

    # Convert to SyncSessionSummary objects
    session_summaries = [SyncSessionSummary(**item) for item in result["items"]]

    return PaginationResponse(
        items=session_summaries,
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        pages=result["pages"],
    )


@sessions_router.get("/{session_id}", response_model=SyncSessionResponse)
async def get_sync_session(
    session_id: str,
    current_user=Depends(require_viewer),
    sync_service: RealSyncService = Depends(get_sync_service),
) -> SyncSessionResponse:
    """
    Get detailed sync session information.

    Args:
        session_id: Session ID
        current_user: Current authenticated user

    Returns:
        SyncSessionResponse: Detailed session information
    """
    logger.info(f"User {current_user.username} requested sync session {session_id}")

    # Get session through real service layer
    session_data = await sync_service.get_session_by_id(session_id)
    if not session_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    return SyncSessionResponse(**session_data)


@sessions_router.post("/", response_model=SyncSessionResponse)
async def create_sync_session(
    request: SyncSessionCreateRequest,
    current_user=Depends(require_analyst),
    sync_service: RealSyncService = Depends(get_sync_service),
) -> SyncSessionResponse:
    """
    Create and start new sync session.

    Args:
        request: Sync session creation request
        current_user: Current authenticated user

    Returns:
        SyncSessionResponse: Created session information
    """
    logger.info(f"User {current_user.username} requested new sync session")

    # Create sync session through real service layer
    session_data = await sync_service.create_sync_session(
        file_path=request.file_path,
        session_type=request.session_type,
        force=request.force
    )

    return SyncSessionResponse(**session_data)


@sessions_router.delete("/{session_id}")
async def cancel_sync_session(
    session_id: str, current_user=Depends(require_analyst)
) -> dict[str, str]:
    """
    Cancel running sync session.

    Args:
        session_id: Session ID to cancel
        current_user: Current authenticated user

    Returns:
        dict: Success message
    """
    logger.info(f"User {current_user.username} requested to cancel session {session_id}")

    # TODO: Implement session cancellation logic
    # This would involve:
    # 1. Check if session is running
    # 2. Signal cancellation to orchestrator
    # 3. Update session status

    return {"message": f"Sync session {session_id} cancellation requested"}


@sessions_router.get("/{session_id}/logs")
async def get_session_logs(session_id: str, current_user=Depends(require_viewer)) -> list[dict]:
    """
    Get sync session logs.

    Args:
        session_id: Session ID
        current_user: Current authenticated user

    Returns:
        list[dict]: Session logs
    """
    logger.info(f"User {current_user.username} requested logs for session {session_id}")

    # TODO: Get actual logs from logging system
    return [
        {
            "timestamp": datetime(2024, 1, 15, 3, 0, 0).isoformat(),
            "level": "INFO",
            "message": "Starting sync session",
            "component": "orchestrator",
        },
        {
            "timestamp": datetime(2024, 1, 15, 3, 0, 30).isoformat(),
            "level": "INFO",
            "message": "File retrieved successfully",
            "component": "file_system",
        },
        {
            "timestamp": datetime(2024, 1, 15, 3, 1, 15).isoformat(),
            "level": "INFO",
            "message": "Parsed 25 deals, 75 items",
            "component": "excel_parser",
        },
    ]


@sessions_router.get("/stats/summary", response_model=SyncStatsResponse)
async def get_sync_stats(current_user=Depends(require_viewer)) -> SyncStatsResponse:
    """
    Get sync session statistics.

    Args:
        current_user: Current authenticated user

    Returns:
        SyncStatsResponse: Sync statistics
    """
    logger.info(f"User {current_user.username} requested sync statistics")

    # TODO: Calculate real statistics from database
    return SyncStatsResponse(
        total_sessions=50,
        successful_sessions=45,
        failed_sessions=5,
        success_rate=90.0,
        avg_duration_seconds=285.0,
        total_deals_synchronized=1250,
        last_sync_at=datetime(2024, 1, 15, 3, 0, 0),
        sync_frequency_days=[
            {"date": "2024-01-15", "sessions": 1},
            {"date": "2024-01-14", "sessions": 1},
            {"date": "2024-01-13", "sessions": 2},
            {"date": "2024-01-12", "sessions": 1},
            {"date": "2024-01-11", "sessions": 1},
            {"date": "2024-01-10", "sessions": 1},
            {"date": "2024-01-09", "sessions": 1},
        ],
    )
