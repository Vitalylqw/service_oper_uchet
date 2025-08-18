# Service Oper Uchet - Обзор проекта

## Описание и цель проекта
Система учета операций для парсинга Excel файлов и загрузки данных в PostgreSQL. Проект включает:
- FastAPI backend с DDD архитектурой
- React frontend с TypeScript
- PostgreSQL база данных
- Система парсинга Excel с валидацией
- API для управления данными

## Архитектура проекта
- **Domain Layer** (`src/domain/`) - бизнес-логика и модели
- **Application Layer** (`src/application/`) - сервисы и use cases
- **Infrastructure Layer** (`src/infrastructure/`) - БД, внешние сервисы
- **Presentation Layer** (`src/presentation/`) - API и веб-интерфейс

## Технологический стек
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic
- **Frontend**: React 18, TypeScript, Vite, TanStack Query
- **Database**: PostgreSQL 16
- **Dev Environment**: Dev Container, Docker Compose

## Структура проекта
```
src/
├── domain/          # Бизнес-модели и логика
├── application/     # Сервисы и use cases
├── infrastructure/  # БД, внешние API
└── presentation/    # API и веб-интерфейс
    ├── api/        # FastAPI endpoints
    └── web/        # React приложение
```

## Принципы разработки
- DDD (Domain-Driven Design)
- Слоистая архитектура
- Асинхронное программирование
- Типизация (PEP 484)
- Логирование через loguru
- Тестирование через pytest
