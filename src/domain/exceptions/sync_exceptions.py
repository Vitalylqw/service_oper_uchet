"""
Sync-related domain exceptions.

Contains exceptions specific to synchronization operations.
"""

from typing import Optional
from uuid import UUID

from .base import BusinessLogicError, DomainException, ValidationError


class SyncError(DomainException):
    """Base sync-related error."""

    def __init__(
        self, session_id: Optional[UUID], message: str, details: Optional[str] = None
    ) -> None:
        """Initialize sync error."""
        self.session_id = session_id
        session_info = f" (Session ID: {session_id})" if session_id else ""
        super().__init__(f"Sync error{session_info}: {message}", details)


class SyncValidationError(ValidationError):
    """Sync validation error."""

    def __init__(self, session_id: Optional[UUID], field: str, value: str, message: str) -> None:
        """Initialize sync validation error."""
        self.session_id = session_id
        super().__init__(field, value, message)


class SyncSessionError(BusinessLogicError):
    """Sync session business logic error."""

    def __init__(self, session_id: UUID, operation: str, message: str) -> None:
        """Initialize sync session error."""
        self.session_id = session_id
        super().__init__(operation, message, f"Session ID: {session_id}")


class SyncFileError(SyncError):
    """Sync file-related error."""

    def __init__(self, file_path: str, message: str, details: Optional[str] = None) -> None:
        """Initialize sync file error."""
        self.file_path = file_path
        super().__init__(None, f"File error for '{file_path}': {message}", details)


class SyncDataIntegrityError(BusinessLogicError):
    """Sync data integrity error."""

    def __init__(self, session_id: UUID, data_type: str, message: str) -> None:
        """Initialize sync data integrity error."""
        self.session_id = session_id
        self.data_type = data_type
        super().__init__(f"data_integrity_{data_type}", message, f"Session ID: {session_id}")


class SyncAlreadyRunningError(BusinessLogicError):
    """Sync already running error."""

    def __init__(self, running_session_id: UUID) -> None:
        """Initialize sync already running error."""
        self.running_session_id = running_session_id
        super().__init__(
            "sync_already_running",
            "Another sync session is already running",
            f"Running Session ID: {running_session_id}",
        )
