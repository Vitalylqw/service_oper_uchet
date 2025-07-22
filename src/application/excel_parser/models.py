"""
Models for Excel parser application service.

Contains Pydantic models for parsing results and statistics.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ...domain.models import Deal, SyncSession


class ParseStats(BaseModel):
    """Statistics of parsing operation."""

    total_sheets: int = Field(default=0, description="Total sheets processed")
    processed_sheets: int = Field(default=0, description="Successfully processed sheets")
    failed_sheets: int = Field(default=0, description="Failed sheets")

    total_deals: int = Field(default=0, description="Total deals found")
    processed_deals: int = Field(default=0, description="Successfully processed deals")
    failed_deals: int = Field(default=0, description="Failed deals")

    total_items: int = Field(default=0, description="Total items found")
    processed_items: int = Field(default=0, description="Successfully processed items")
    failed_items: int = Field(default=0, description="Failed items")

    errors: list[str] = Field(default_factory=list, description="List of errors")
    warnings: list[str] = Field(default_factory=list, description="List of warnings")

    @property
    def success_rate_sheets(self) -> float:
        """Success rate for sheets processing."""
        if self.total_sheets == 0:
            return 0.0
        return (self.processed_sheets / self.total_sheets) * 100

    @property
    def success_rate_deals(self) -> float:
        """Success rate for deals processing."""
        if self.total_deals == 0:
            return 0.0
        return (self.processed_deals / self.total_deals) * 100

    @property
    def success_rate_items(self) -> float:
        """Success rate for items processing."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100


class ParseResult(BaseModel):
    """Result of Excel parsing operation."""

    deals: list[Deal] = Field(default_factory=list, description="Parsed deals")
    stats: ParseStats = Field(default_factory=ParseStats, description="Parsing statistics")
    sync_session: SyncSession = Field(..., description="Associated sync session")

    # Метаданные
    file_path: str = Field(..., description="Path to parsed file")
    file_size: int = Field(..., description="File size in bytes")
    file_hash: str = Field(..., description="File hash for integrity check")
    parsed_at: datetime = Field(default_factory=datetime.now, description="Parse timestamp")

    @property
    def total_deals(self) -> int:
        """Total number of deals."""
        return len(self.deals)

    @property
    def total_items(self) -> int:
        """Total number of items across all deals."""
        return sum(len(deal.items) for deal in self.deals)

    @property
    def has_errors(self) -> bool:
        """Check if parsing had errors."""
        return len(self.stats.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if parsing had warnings."""
        return len(self.stats.warnings) > 0

    def get_deals_by_period(self, month: str, year: str) -> list[Deal]:
        """Get deals filtered by period."""
        return [
            deal for deal in self.deals
            if deal.period.month == month and deal.period.year == year
        ]

    def get_deals_by_client(self, client_name: str) -> list[Deal]:
        """Get deals filtered by client name."""
        return [
            deal for deal in self.deals
            if client_name.lower() in deal.client_name.lower()
        ]
