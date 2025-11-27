"""
Value Objects для domain слоя.

Содержит неизменяемые объекты-значения:
- Money: Денежные суммы с валютой (только положительные, 2 знака)
- SignedMoney: Денежные суммы с валютой (могут быть отрицательными, 2 знака)
- Money5: Денежные суммы с валютой (только положительные, 5 знаков)
- SignedMoney5: Денежные суммы с валютой (могут быть отрицательными, 5 знаков)
- DebtMoney: Денежные суммы для долгов (всегда отрицательные)
- Period: Временной период (месяц, год)
- HashKey: Ключ для быстрого сравнения
- Status: Статус операции
"""

from .common import (
    HashKey,
    Money,
    Money5,
    SignedMoney,
    SignedMoney5,
    DebtMoney,
    Period,
    Status,
)

__all__ = [
    "Money",
    "Money5",
    "SignedMoney",
    "SignedMoney5",
    "DebtMoney",
    "Period",
    "HashKey",
    "Status",
]
