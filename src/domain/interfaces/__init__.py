"""
Domain interfaces.

Contains abstract repository interfaces for dependency inversion.
"""

from .repository_interfaces import (
    DealRepository,
    EventStore,
    ReadModelRepository,
    SyncSessionRepository,
)

__all__ = [
    "DealRepository",
    "SyncSessionRepository",
    "EventStore",
    "ReadModelRepository",
]
