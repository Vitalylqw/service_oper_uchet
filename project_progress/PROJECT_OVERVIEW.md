# Service Oper Uchet - Обзор проекта

## Описание и цель проекта
Система учета операций для парсинга Excel файлов и загрузки данных в PostgreSQL. Проект включает:
- DDD-архитектура (domain, application, infrastructure)
- PostgreSQL (и SQLite для разработки) база данных
- Система парсинга Excel с валидацией
- Event Sourcing, CQRS, read-модели

## Архитектура проекта
- **Domain Layer** (`src/domain/`) - бизнес-логика и модели
- **Application Layer** (`src/application/`) - сервисы и use cases
- **Infrastructure Layer** (`src/infrastructure/`) - БД, воркеры, репозитории

## Технологический стек
- **Backend**: Python 3.9+, SQLAlchemy, Alembic, loguru
- **Database**: PostgreSQL 16 / SQLite
- **Dev Environment**: Dev Container, Docker Compose (БД)

## Структура проекта
```
src/
├── domain/          # Бизнес-модели и логика
├── application/     # Сервисы и use cases
├── infrastructure/  # БД, воркеры, репозитории
```

## Среда разработки (Dev Container + Remote-SSH)
- Проект открыт на удалённом сервере по SSH; в контейнере путь `/workspaces/service_oper_uchet`. Локальной папки проекта на Windows нет.
- **Файловый менеджер к проекту:** (1) Cursor — левая панель (Explorer) уже показывает файлы на сервере. (2) Проводник Windows: смонтировать каталог сервера через SSHFS (WinFsp + SSHFS-Win) как сетевой диск и открыть его в Explorer. (3) SFTP-клиент (WinSCP, FileZilla): подключиться к тому же серверу и перейти в каталог проекта.

## Принципы разработки
- DDD (Domain-Driven Design)
- Слоистая архитектура
- Асинхронное программирование
- Типизация (PEP 484)
- Логирование через loguru
- Тестирование через pytest
