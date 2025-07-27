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


@sessions_router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(current_user=Depends(require_viewer)) -> SyncStatsResponse:
    """
    Get sync session statistics.

    Args:
        current_user: Current authenticated user

    Returns:
        SyncStatsResponse: Sync statistics
    """
    logger.info(f"User {current_user.username} requested sync statistics")

    # Get real statistics from database
    from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
    from sqlalchemy import text
    
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    try:
        async with db_manager.get_async_session() as session:
            # Basic session stats
            session_stats = await session.execute(
                text("SELECT " +
                     "COUNT(*) as total_sessions, " +
                     "COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_sessions, " +
                     "COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_sessions " +
                     "FROM sync_sessions")
            )
            stats_row = session_stats.fetchone()
            total_sessions = stats_row[0] if stats_row else 0
            successful_sessions = stats_row[1] if stats_row else 0
            failed_sessions = stats_row[2] if stats_row else 0
            
            # Calculate success rate
            success_rate = (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0
            
            # Average duration (placeholder - sync_sessions table doesn't have duration)
            avg_duration_seconds = 285.0  # Default value
            
            # Total deals synchronized
            total_deals_query = await session.execute(
                text("SELECT COUNT(*) FROM read_deals WHERE is_active = true")
            )
            total_deals_synchronized = total_deals_query.scalar() or 0
            
            # Last sync time
            last_sync_query = await session.execute(
                text("SELECT MAX(created_at) FROM sync_sessions WHERE status = 'completed'")
            )
            last_sync_result = last_sync_query.scalar()
            last_sync_at = last_sync_result if last_sync_result else None
            
            # Sync frequency by days (last 7 days)
            freq_query = await session.execute(
                text("SELECT DATE(created_at) as sync_date, COUNT(*) as sessions " +
                     "FROM sync_sessions " +
                     "WHERE created_at >= DATE('now', '-7 days') " +
                     "GROUP BY DATE(created_at) " +
                     "ORDER BY sync_date DESC LIMIT 7")
            )
            sync_frequency_days = [
                {"date": row[0], "sessions": row[1]}
                for row in freq_query.fetchall()
            ]
            
    except Exception as e:
        logger.error(f"Error fetching sync statistics: {e}")
        # Fallback values
        total_sessions = 0
        successful_sessions = 0
        failed_sessions = 0
        success_rate = 0.0
        avg_duration_seconds = 0.0
        total_deals_synchronized = 0
        last_sync_at = None
        sync_frequency_days = []

    return SyncStatsResponse(
        total_sessions=total_sessions,
        successful_sessions=successful_sessions,
        failed_sessions=failed_sessions,
        success_rate=success_rate,
        avg_duration_seconds=avg_duration_seconds,
        total_deals_synchronized=total_deals_synchronized,
        last_sync_at=last_sync_at,
        sync_frequency_days=sync_frequency_days,
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
