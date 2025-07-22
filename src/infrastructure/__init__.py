"""
Infrastructure Layer - работа с внешними системами.

Содержит:
- database/: PostgreSQL, Event Store, Read Models
- file_system/: Получение файлов (SMB/FTP/HTTP)
- scheduler/: APScheduler + Windows Task Scheduler резерв
- monitoring/: Loguru + Prometheus метрики
- notifications/: Email алерты

Технологии: SQLAlchemy 2.0, Alembic, Redis
Покрытие тестами: 85%
"""
