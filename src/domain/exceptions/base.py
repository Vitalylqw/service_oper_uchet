"""
Base domain exceptions.

Contains base exception classes for domain layer.
"""

from typing import Optional


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        """Initialize domain exception."""
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """String representation."""
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class ValidationError(DomainException):
    """Validation error in domain logic."""

    def __init__(self, field: str, value: str, message: str) -> None:
        """Initialize validation error."""
        self.field = field
        self.value = value
        super().__init__(f"Validation error for field '{field}': {message}")


class BusinessLogicError(DomainException):
    """Business logic violation error."""

    def __init__(self, operation: str, message: str, context: Optional[str] = None) -> None:
        """Initialize business logic error."""
        self.operation = operation
        self.context = context
        super().__init__(f"Business logic error in '{operation}': {message}", context)
