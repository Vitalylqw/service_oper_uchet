"""
Domain exceptions.

Contains domain-specific exceptions for business logic validation.
"""

from .base import BusinessLogicError, DomainException, ValidationError
from .deal_exceptions import DealError, DealItemError, DealValidationError
from .sync_exceptions import SyncError, SyncFileError, SyncSessionError, SyncValidationError

__all__ = [
    "DomainException",
    "ValidationError",
    "BusinessLogicError",
    "DealError",
    "DealValidationError",
    "DealItemError",
    "SyncError",
    "SyncValidationError",
    "SyncSessionError",
    "SyncFileError",
]
