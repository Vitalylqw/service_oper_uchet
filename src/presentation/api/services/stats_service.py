"""
Stats Service for FastAPI endpoints.

Dedicated service for statistics operations using ReadModelRepositoryImplementation
following CQRS pattern - Query side only.
"""

from __future__ import annotations

from loguru import logger

from infrastructure.database.repositories import ReadModelRepositoryImplementation


class StatsService:
    """
    Statistics service for API endpoints.
    
    Handles all statistics-related queries using ReadModelRepository.
    Part of CQRS Query side - read-only operations.
    """

    def __init__(self, read_model_repository: ReadModelRepositoryImplementation) -> None:
        """Initialize stats service with read model repository."""
        self.read_model_repository = read_model_repository
        logger.debug("StatsService initialized with ReadModelRepository")

    async def get_deal_stats(self, period_month: str | None = None, period_year: str | None = None) -> dict:
        """Get aggregated deal statistics from read model repository."""
        try:
            logger.info("Getting deal statistics from read model repository")

            stats = await self.read_model_repository.get_deal_stats(period_month, period_year)

            # Ensure Decimal values are converted to float for JSON serialization
            for key in ("total_revenue", "total_margin", "avg_revenue", "avg_profitability"):
                if key in stats:
                    stats[key] = float(stats[key]) if stats[key] is not None else 0

            logger.debug(f"Retrieved deal stats: {stats['total_deals']} deals, {stats['total_revenue']} revenue")
            return stats

        except Exception as e:
            logger.error(f"Failed to get deal stats from read model: {e}")
            return {
                "total_deals": 0,
                "total_revenue": 0,
                "total_margin": 0,
                "shipped_deals": 0,
                "paid_deals": 0,
                "avg_revenue": 0,
                "avg_profitability": 0,
            }