"""
Domain Layer - предметная область (чистая бизнес-логика).

Содержит:
- models: Pydantic модели (Deal, DealItem, SyncSession)
- value_objects: Money, Period, HashKey, Status
- interfaces: Абстракции репозиториев
- exceptions: Доменные исключения

Правила:
- Никаких внешних зависимостей
- Только чистая бизнес-логика
- 100% покрытие тестами
"""
