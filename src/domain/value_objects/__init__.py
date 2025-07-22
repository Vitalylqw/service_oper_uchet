"""
Value Objects для domain слоя.

Содержит неизменяемые объекты-значения:
- Money: Денежные суммы с валютой
- Period: Временной период (месяц, год)
- HashKey: Ключ для быстрого сравнения
- Status: Статус операции
"""

from .common import HashKey, Money, Period, Status

__all__ = ["Money", "Period", "HashKey", "Status"]
