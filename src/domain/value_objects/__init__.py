"""
Value Objects для domain слоя.

Содержит неизменяемые объекты-значения:
- Money: Денежные суммы с валютой (только положительные)
- SignedMoney: Денежные суммы с валютой (могут быть отрицательными)
- DebtMoney: Денежные суммы для долгов (всегда отрицательные)
- Period: Временной период (месяц, год)
- HashKey: Ключ для быстрого сравнения
- Status: Статус операции
"""

from .common import HashKey, Money, SignedMoney, DebtMoney, Period, Status

__all__ = ["Money", "SignedMoney", "DebtMoney", "Period", "HashKey", "Status"]
