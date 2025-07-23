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

from pydantic import BaseModel, Field, field_validator


class Status(str, Enum):
    """Статус операции или состояния."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SHIPPED = "shipped"
    PAID = "paid"
    CANCELLED = "cancelled"

    @classmethod
    def from_string(cls, value: str) -> Status | None:
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
            "completed": cls.COMPLETED,  # Добавляем английский "completed"
            "отменено": cls.CANCELLED,
            "cancelled": cls.CANCELLED,
        }

        return mapping.get(value_lower, cls.PENDING)


class Money(BaseModel):
    """Денежная сумма с валютой."""

    amount: Decimal = Field(..., description="Сумма")
    currency: str = Field(default="RUB", description="Валюта")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount precision."""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v.quantize(Decimal("0.01"))  # Округляем до копеек

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        if len(v) != 3:
            raise ValueError("Currency code must be 3 characters")
        return v.upper()

    def __str__(self) -> str:
        """String representation."""
        return f"{self.amount} {self.currency}"

    def __add__(self, other: Money) -> Money:
        """Add two money amounts."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        """Subtract two money amounts."""
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, multiplier: Decimal | float | int) -> Money:
        """Multiply money by a number."""
        return Money(amount=self.amount * Decimal(str(multiplier)), currency=self.currency)

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    model_config = {"frozen": True}  # Неизменяемый объект


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
        return v.strip().capitalize()

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        """Validate year."""
        if not re.match(r"^\d{4}$", v.strip()):
            raise ValueError("Year must be 4 digits")
        year_int = int(v)
        if not (2020 <= year_int <= 2030):
            raise ValueError("Year must be between 2020 and 2030")
        return v.strip()

    def __str__(self) -> str:
        """String representation."""
        return self.full_name

    @classmethod
    def from_sheet_name(cls, sheet_name: str) -> Period:
        """Create period from Excel sheet name."""
        if not sheet_name:
            raise ValueError("Sheet name cannot be empty")

        # Словарь месяцев
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

        # Ищем месяц в названии
        found_month = ""
        for month_key, month_value in months_map.items():
            if month_key in sheet_lower:
                found_month = month_value
                break

        if not found_month:
            raise ValueError(f"Cannot extract month from sheet name: {sheet_name}")

        # Ищем год в названии (4 цифры)
        year_match = re.search(r"\b(\d{4})\b", sheet_name)
        if not year_match:
            raise ValueError(f"Cannot extract year from sheet name: {sheet_name}")

        found_year = year_match.group(1)

        return cls(month=found_month, year=found_year, full_name=sheet_name.strip())

    model_config = {"frozen": True}  # Неизменяемый объект


class HashKey(BaseModel):
    """Ключ для быстрого сравнения объектов."""

    value: str = Field(..., description="Hash значение")
    algorithm: str = Field(default="md5", description="Алгоритм хеширования")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Validate hash value format."""
        if not v:
            raise ValueError("Hash value cannot be empty")
        if not re.match(r"^[a-f0-9]+$", v.lower()):
            raise ValueError("Hash value must be hexadecimal")
        return v.lower()

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, HashKey):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash(self.value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HashKey:
        """Create hash key from dictionary."""
        # Сортируем ключи для консистентности
        sorted_data = {k: v for k, v in sorted(data.items()) if v is not None}
        json_str = json.dumps(sorted_data, ensure_ascii=False, sort_keys=True)
        hash_value = hashlib.md5(json_str.encode("utf-8")).hexdigest()
        return cls(value=hash_value, algorithm="md5")

    @classmethod
    def from_string(cls, text: str) -> HashKey:
        """Create hash key from string."""
        hash_value = hashlib.md5(text.encode("utf-8")).hexdigest()
        return cls(value=hash_value, algorithm="md5")

    model_config = {"frozen": True}  # Неизменяемый объект
