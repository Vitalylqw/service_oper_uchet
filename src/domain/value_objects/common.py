"""
Common value objects for the domain.

Contains immutable value objects used throughout the system.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Status(str, Enum):
    """Статус операции или состояния."""

    PENDING = "pending"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    SHIPPED = "shipped"
    PAID = "paid"
    CANCELLED = "cancelled"

    @classmethod
    def from_string(cls, value: str) -> "Status | None":
        """Create status from string representation."""
        if not value:
            return None

        value_lower = value.lower().strip()

        # Маппинг различных вариантов написания
        mapping = {
            "да": cls.COMPLETED,
            "нет": cls.PENDING,
            "отгружен": cls.SHIPPED,
            "shipped": cls.SHIPPED,
            "оплачен": cls.PAID,
            "paid": cls.PAID,
            "выполнено": cls.COMPLETED,
            "готово": cls.COMPLETED,
            "completed": cls.COMPLETED,
            "partial": cls.PARTIAL,
            "частично": cls.PARTIAL,
            "отменено": cls.CANCELLED,
            "cancelled": cls.CANCELLED,
        }

        return mapping.get(value_lower, cls.PENDING)


# ---------------------------------------------------------------------------
#  Money types (RUB-only, no currency field)
# ---------------------------------------------------------------------------


class Money(BaseModel):
    """Positive money amount in Russian roubles."""

    amount: Decimal = Field(..., description="Amount in RUB (positive)")

    # Validators -----------------------------------------------------------------
    @field_validator("amount")
    @classmethod
    def _round(cls, v: Decimal) -> Decimal:  # noqa: D401 – simple helper
        """Round to two decimals, ensure non-negative."""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v.quantize(Decimal("0.01"))

    # Dunder methods -------------------------------------------------------------
    def __str__(self) -> str:  # pragma: no cover – trivial
        return f"{self.amount}"

    def __add__(self, other: "Money") -> "Money":
        return Money(amount=self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(amount=self.amount - other.amount)

    def __mul__(self, multiplier: int | float | Decimal) -> "Money":
        return Money(amount=self.amount * Decimal(str(multiplier)))

    def __eq__(self, other: object) -> bool:  # noqa: D401 – custom equality
        return isinstance(other, Money) and self.amount == other.amount

    model_config = ConfigDict(frozen=True, validate_assignment=True)


class SignedMoney(BaseModel):
    """Money that can be positive or negative (RUB)."""

    amount: Decimal = Field(..., description="Signed amount in RUB")

    @field_validator("amount")
    @classmethod
    def _round(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))

    # Dunder / helpers -----------------------------------------------------------
    def __str__(self) -> str:  # pragma: no cover
        return f"{self.amount}"

    def __add__(self, other: "SignedMoney") -> "SignedMoney":
        return SignedMoney(amount=self.amount + other.amount)

    def __sub__(self, other: "SignedMoney") -> "SignedMoney":
        return SignedMoney(amount=self.amount - other.amount)

    def __mul__(self, multiplier: int | float | Decimal) -> "SignedMoney":
        return SignedMoney(amount=self.amount * Decimal(str(multiplier)))

    def __eq__(self, other: object) -> bool:  # noqa: D401
        return isinstance(other, SignedMoney) and self.amount == other.amount

    # Convenience flags ----------------------------------------------------------
    @property
    def is_positive(self) -> bool:  # noqa: D401
        return self.amount > 0

    @property
    def is_negative(self) -> bool:  # noqa: D401
        return self.amount < 0

    @property
    def is_zero(self) -> bool:  # noqa: D401
        return self.amount == 0

    def abs(self) -> Money:
        return Money(amount=abs(self.amount))

    model_config = ConfigDict(frozen=True, validate_assignment=True)


class DebtMoney(BaseModel):
    """Debt amount (always negative, RUB)."""

    amount: Decimal = Field(..., description="Negative amount in RUB")

    @field_validator("amount")
    @classmethod
    def _round(cls, v: Decimal) -> Decimal:
        if v >= 0:
            raise ValueError("Debt amount must be negative")
        return v.quantize(Decimal("0.01"))

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.amount}"

    def __add__(self, other: "DebtMoney") -> "DebtMoney":
        return DebtMoney(amount=self.amount + other.amount)

    def __sub__(self, other: "DebtMoney") -> "DebtMoney":
        return DebtMoney(amount=self.amount - other.amount)

    def __mul__(self, multiplier: int | float | Decimal) -> "DebtMoney":
        return DebtMoney(amount=self.amount * Decimal(str(multiplier)))

    def __eq__(self, other: object) -> bool:  # noqa: D401
        return isinstance(other, DebtMoney) and self.amount == other.amount

    @property
    def absolute_value(self) -> Money:
        return Money(amount=abs(self.amount))

    model_config = ConfigDict(frozen=True, validate_assignment=True)


# ---------------------------------------------------------------------------
#  Period & HashKey  (unchanged)
# ---------------------------------------------------------------------------


class Period(BaseModel):
    """Временной период (месяц и год)."""

    month: str = Field(..., description="Название месяца")
    year: str = Field(..., description="Год")
    full_name: str = Field(..., description="Полное название периода")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        """Validate month name."""
        valid_months = {
            "январь",
            "февраль",
            "март",
            "апрель",
            "май",
            "июнь",
            "июль",
            "август",
            "сентябрь",
            "октябрь",
            "ноябрь",
            "декабрь",
        }

        month_lower = v.lower().strip()
        if month_lower not in valid_months:
            raise ValueError(f"Invalid month name: {v}")

        months_map = {
            "январь": "Январь",
            "февраль": "Февраль",
            "март": "Март",
            "апрель": "Апрель",
            "май": "Май",
            "июнь": "Июнь",
            "июль": "Июль",
            "август": "Август",
            "сентябрь": "Сентябрь",
            "октябрь": "Октябрь",
            "ноябрь": "Ноябрь",
            "декабрь": "Декабрь",
        }
        return months_map[month_lower]

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        """Validate year (YYYY, 2020-2030)."""
        if not re.match(r"^\d{4}$", v.strip()):
            raise ValueError("Year must be 4 digits")
        year_int = int(v)
        if not (2020 <= year_int <= 2030):
            raise ValueError("Year must be between 2020 and 2030")
        return v.strip()

    def __str__(self) -> str:  # pragma: no cover
        return self.full_name

    @classmethod
    def from_sheet_name(cls, sheet_name: str) -> "Period":
        """Create period from Excel sheet name (ru month + YYYY)."""
        if not sheet_name:
            raise ValueError("Sheet name cannot be empty")

        months_map = {
            "январь": "Январь",
            "февраль": "Февраль",
            "март": "Март",
            "апрель": "Апрель",
            "май": "Май",
            "июнь": "Июнь",
            "июль": "Июль",
            "август": "Август",
            "сентябрь": "Сентябрь",
            "октябрь": "Октябрь",
            "ноябрь": "Ноябрь",
            "декабрь": "Декабрь",
        }

        sheet_lower = sheet_name.lower().strip()
        found_month = next((val for key, val in months_map.items() if key in sheet_lower), "")
        if not found_month:
            raise ValueError(f"Cannot extract month from sheet name: {sheet_name}")

        year_match = re.search(r"\b(\d{4})\b", sheet_name)
        if not year_match:
            raise ValueError(f"Cannot extract year from sheet name: {sheet_name}")

        return cls(month=found_month, year=year_match.group(1), full_name=sheet_name.strip())

    model_config = ConfigDict(frozen=True, validate_assignment=True)


class HashKey(BaseModel):
    """Ключ для быстрого сравнения объектов."""

    value: str = Field(..., description="Hash значение")
    algorithm: str = Field(default="md5", description="Алгоритм хеширования")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        if not v:
            raise ValueError("Hash value cannot be empty")
        if not re.match(r"^[a-f0-9]+$", v.lower()):
            raise ValueError("Hash value must be hexadecimal")
        return v.lower()

    def __str__(self) -> str:  # pragma: no cover
        return self.value

    def __eq__(self, other: object) -> bool:  # noqa: D401
        return isinstance(other, HashKey) and self.value == other.value

    def __hash__(self) -> int:  # noqa: D401
        return hash(self.value)

    # Utility helpers -----------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HashKey":
        sorted_data = {k: v for k, v in sorted(data.items()) if v is not None}
        json_str = json.dumps(sorted_data, ensure_ascii=False, sort_keys=True)
        return cls(value=hashlib.md5(json_str.encode("utf-8")).hexdigest())

    @classmethod
    def from_string(cls, text: str) -> "HashKey":
        return cls(value=hashlib.md5(text.encode("utf-8")).hexdigest())

    model_config = ConfigDict(frozen=True, validate_assignment=True)
