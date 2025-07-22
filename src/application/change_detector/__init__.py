"""
Change Detector Application Service.

Contains algorithms for comparing Excel data with database state
and identifying changes (INSERT, UPDATE, DELETE) for incremental synchronization.
"""

from .detector import ChangeDetectorService
from .models import ChangeDetectionResult, ChangeType, EntityChange

__all__ = [
    "ChangeDetectorService",
    "ChangeDetectionResult",
    "ChangeType",
    "EntityChange",
]
