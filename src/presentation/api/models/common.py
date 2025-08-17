"""
Common API models.

Contains shared models for pagination, filtering, and common response patterns.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and limit."""
        return (self.page - 1) * self.limit


class PaginationResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int
    size: int = Field(alias="limit", description="Items per page (alias for limit)")
    
    def model_post_init(self, __context) -> None:
        """Set size field to match limit value."""
        self.size = self.limit
    
    @classmethod
    def create(cls, items: list[T], total: int, pagination: PaginationParams) -> PaginationResponse[T]:
        """
        Create paginated response.
        
        Args:
            items: List of items for current page
            total: Total number of items
            pagination: Pagination parameters
            
        Returns:
            PaginationResponse: Paginated response
        """
        pages = (total + pagination.limit - 1) // pagination.limit
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            pages=pages
        )


class FilterParams(BaseModel):
    """Base filter parameters."""
    
    search: str | None = Field(default=None, description="Search query")
    sort_by: str | None = Field(default=None, description="Sort field")
    sort_order: str = Field(default="asc", description="Sort order (asc/desc)")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str
    error_code: str | None = None
    timestamp: str | None = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    message: str
    data: dict[str, Any] | None = None 