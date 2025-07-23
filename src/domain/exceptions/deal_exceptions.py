"""
Deal-related domain exceptions.

Contains exceptions specific to deal and deal item operations.
"""

from typing import Optional
from uuid import UUID

from .base import BusinessLogicError, DomainException, ValidationError


class DealError(DomainException):
    """Base deal-related error."""

    def __init__(
        self, deal_id: Optional[UUID], message: str, details: Optional[str] = None
    ) -> None:
        """Initialize deal error."""
        self.deal_id = deal_id
        deal_info = f" (Deal ID: {deal_id})" if deal_id else ""
        super().__init__(f"Deal error{deal_info}: {message}", details)


class DealValidationError(ValidationError):
    """Deal validation error."""

    def __init__(self, deal_id: Optional[UUID], field: str, value: str, message: str) -> None:
        """Initialize deal validation error."""
        self.deal_id = deal_id
        super().__init__(field, value, message)


class DealItemError(DomainException):
    """Deal item related error."""

    def __init__(
        self,
        deal_id: Optional[UUID],
        item_id: Optional[UUID],
        message: str,
        details: Optional[str] = None,
    ) -> None:
        """Initialize deal item error."""
        self.deal_id = deal_id
        self.item_id = item_id

        info_parts = []
        if deal_id:
            info_parts.append(f"Deal ID: {deal_id}")
        if item_id:
            info_parts.append(f"Item ID: {item_id}")

        info = f" ({', '.join(info_parts)})" if info_parts else ""
        super().__init__(f"Deal item error{info}: {message}", details)


class DealCalculationError(BusinessLogicError):
    """Deal calculation error."""

    def __init__(self, deal_id: UUID, calculation_type: str, message: str) -> None:
        """Initialize deal calculation error."""
        self.deal_id = deal_id
        self.calculation_type = calculation_type
        super().__init__(f"deal_calculation_{calculation_type}", message, f"Deal ID: {deal_id}")


class DealDuplicateError(BusinessLogicError):
    """Deal duplicate error."""

    def __init__(self, deal_key: str, existing_deal_id: UUID) -> None:
        """Initialize deal duplicate error."""
        self.deal_key = deal_key
        self.existing_deal_id = existing_deal_id
        super().__init__(
            "deal_duplicate_check",
            f"Deal with key '{deal_key}' already exists",
            f"Existing Deal ID: {existing_deal_id}",
        )
