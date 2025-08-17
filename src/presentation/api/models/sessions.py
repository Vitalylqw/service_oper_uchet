"""
Sync session API models.

Contains Pydantic models for sync session related API requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import FilterParams


class SyncSessionResponse(BaseModel):
    """Sync session response model."""
    
    id: str
    session_type: str
    status: str
    
    # Timing
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    
    # File information
    file_path: str
    file_hash: str | None = None
    file_size_bytes: int | None = None
    
    # Statistics
    total_deals_processed: int = 0
    total_items_processed: int = 0
    insertions_count: int = 0
    updates_count: int = 0
    deletions_count: int = 0
    errors_count: int = 0
    
    # Results
    success: bool = False
    error_message: str | None = None
    
    # Performance metrics
    parsing_duration_seconds: float | None = None
    change_detection_duration_seconds: float | None = None
    database_duration_seconds: float | None = None
    
    # Metadata
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncSessionSummary(BaseModel):
    """Sync session summary for list views."""
    
    id: str
    session_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    total_deals_processed: int
    success: bool
    error_message: str | None = None


class SyncSessionListItem(BaseModel):
    """Sync session list item for frontend compatibility."""
    
    id: str
    session_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    total_deals_processed: int
    success: bool
    error_message: str | None = None
    
    # Frontend-compatible fields
    processed_count: int = 0
    changed_count: int = 0
    error_count: int = 0


class SyncSessionFilters(FilterParams):
    """Sync session filter parameters."""
    
    session_type: str | None = Field(default=None, description="Filter by session type")
    status: str | None = Field(default=None, description="Filter by status")
    success: bool | None = Field(default=None, description="Filter by success status")
    date_from: datetime | None = Field(default=None, description="Filter by date from")
    date_to: datetime | None = Field(default=None, description="Filter by date to")


class SyncStatsResponse(BaseModel):
    """Sync statistics response."""
    
    total_sessions: int
    successful_sessions: int
    failed_sessions: int
    success_rate: float
    avg_duration_seconds: float
    total_deals_synchronized: int
    last_sync_at: datetime | None = None
    sync_frequency_days: list[dict[str, str | int]]  # Sessions per day for last week


class SyncSessionCreateRequest(BaseModel):
    """Request to create a new sync session."""
    
    session_type: str = Field(..., description="Type of sync (full/incremental)")
    file_path: str = Field(..., min_length=1, description="Path to Excel file")
    force: bool = Field(default=False, description="Force sync even if file unchanged") 