"""
Real services for FastAPI endpoints.

Contains wrapper services that integrate domain/infrastructure layers
with FastAPI presentation layer, replacing mock services.
"""

from .real_deal_service import RealDealService
from .real_health_service import RealHealthService
from .real_sync_service import RealSyncService
from .stats_service import StatsService

__all__ = [
    "RealDealService",
    "RealSyncService", 
    "RealHealthService",
    "StatsService",
]
