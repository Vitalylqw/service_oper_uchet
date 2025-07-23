"""
Models for data validation.

Contains Pydantic models for validation results, errors and warnings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Блокирует обработку полностью
    ERROR = "error"  # Блокирует обработку конкретной записи
    WARNING = "warning"  # Не блокирует, но требует внимания
    INFO = "info"  # Информационное сообщение


class ValidationError(BaseModel):
    """Validation error or warning."""

    severity: ErrorSeverity = Field(..., description="Error severity level")
    code: str = Field(..., description="Error code for categorization")
    message: str = Field(..., description="Human-readable error message")

    # Контекст ошибки
    sheet_name: str | None = Field(None, description="Excel sheet name")
    row_number: int | None = Field(None, description="Row number in Excel (1-based)")
    column_name: str | None = Field(None, description="Column name")
    cell_value: Any | None = Field(None, description="Actual cell value")
    expected_value: Any | None = Field(None, description="Expected value or format")

    # Дополнительный контекст
    deal_key: str | None = Field(None, description="Deal key if applicable")
    item_key: str | None = Field(None, description="Item key if applicable")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")

    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_blocking(self) -> bool:
        """Check if this error blocks processing."""
        return self.severity in {ErrorSeverity.CRITICAL, ErrorSeverity.ERROR}

    @property
    def location_info(self) -> str:
        """Get human-readable location information."""
        parts = []
        if self.sheet_name:
            parts.append(f"лист '{self.sheet_name}'")
        if self.row_number:
            parts.append(f"строка {self.row_number}")
        if self.column_name:
            parts.append(f"колонка '{self.column_name}'")

        return ", ".join(parts) if parts else "неизвестно"

    def __str__(self) -> str:
        """String representation of the error."""
        location = f" ({self.location_info})" if self.location_info != "неизвестно" else ""
        return f"[{self.severity.upper()}] {self.message}{location}"


class ValidationWarning(ValidationError):
    """Convenience class for warnings."""

    def __init__(self, **data):
        if "severity" not in data:
            data["severity"] = ErrorSeverity.WARNING
        super().__init__(**data)


class ValidationStats(BaseModel):
    """Statistics of validation operation."""

    total_sheets: int = Field(default=0, description="Total sheets checked")
    valid_sheets: int = Field(default=0, description="Valid sheets")

    total_deals: int = Field(default=0, description="Total deals checked")
    valid_deals: int = Field(default=0, description="Valid deals")
    invalid_deals: int = Field(default=0, description="Invalid deals")

    total_items: int = Field(default=0, description="Total items checked")
    valid_items: int = Field(default=0, description="Valid items")
    invalid_items: int = Field(default=0, description="Invalid items")

    critical_errors: int = Field(default=0, description="Critical errors count")
    errors: int = Field(default=0, description="Errors count")
    warnings: int = Field(default=0, description="Warnings count")

    @property
    def total_issues(self) -> int:
        """Total number of issues found."""
        return self.critical_errors + self.errors + self.warnings

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are blocking issues."""
        return self.critical_errors > 0 or self.errors > 0

    @property
    def success_rate_deals(self) -> float:
        """Success rate for deals validation."""
        if self.total_deals == 0:
            return 100.0
        return (self.valid_deals / self.total_deals) * 100

    @property
    def success_rate_items(self) -> float:
        """Success rate for items validation."""
        if self.total_items == 0:
            return 100.0
        return (self.valid_items / self.total_items) * 100


class ValidationResult(BaseModel):
    """Result of data validation operation."""

    is_valid: bool = Field(..., description="Overall validation result")
    issues: list[ValidationError] = Field(
        default_factory=list, description="List of validation issues"
    )
    stats: ValidationStats = Field(
        default_factory=ValidationStats, description="Validation statistics"
    )

    # Контекст валидации
    file_path: str = Field(..., description="Path to validated file")
    validated_at: datetime = Field(default_factory=datetime.now, description="Validation timestamp")
    validator_version: str = Field(default="1.0", description="Validator version")

    def add_error(self, error: ValidationError) -> None:
        """Add validation error."""
        self.issues.append(error)

        # Обновляем статистику
        if error.severity == ErrorSeverity.CRITICAL:
            self.stats.critical_errors += 1
        elif error.severity == ErrorSeverity.ERROR:
            self.stats.errors += 1
        elif error.severity == ErrorSeverity.WARNING:
            self.stats.warnings += 1

        # Проверяем общую валидность
        if error.is_blocking:
            self.is_valid = False

    def add_warning(self, code: str, message: str, **context) -> None:
        """Add validation warning."""
        warning = ValidationWarning(code=code, message=message, **context)
        self.add_error(warning)

    def get_errors_by_severity(self, severity: ErrorSeverity) -> list[ValidationError]:
        """Get errors by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_blocking_errors(self) -> list[ValidationError]:
        """Get all blocking errors."""
        return [issue for issue in self.issues if issue.is_blocking]

    def get_errors_by_sheet(self, sheet_name: str) -> list[ValidationError]:
        """Get errors for specific sheet."""
        return [issue for issue in self.issues if issue.sheet_name == sheet_name]

    @property
    def has_critical_errors(self) -> bool:
        """Check if there are critical errors."""
        return self.stats.critical_errors > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are errors."""
        return self.stats.errors > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return self.stats.warnings > 0

    @property
    def summary(self) -> str:
        """Get validation summary."""
        if self.is_valid:
            warning_text = f", {self.stats.warnings} предупреждений" if self.has_warnings else ""
            return f"Валидация пройдена успешно{warning_text}"
        else:
            return (
                f"Валидация не пройдена: {self.stats.critical_errors} критических ошибок, "
                f"{self.stats.errors} ошибок, {self.stats.warnings} предупреждений"
            )
