# Service Oper Uchet

Проект синхронизирует данные из Excel с базой данных и поддерживает инженерные артефакты для
проверки результата: `event_store`, `read_deals`, `read_positions`, `read_stats`,
`db_snapshots`.

Текущий scope проекта:

- парсинг Excel;
- определение изменений относительно текущего состояния БД;
- запись событий в `event_store`;
- актуализация read-моделей;
- технические проверки через тесты и dashboard-скрипты.

Удаленный scope, который больше не считается активной частью проекта:

- REST API;
- веб-интерфейс;
- 1С-интеграция;
- ролевой доступ и пользовательская auth-модель.

## Карта документации

- `docs/README.md` — индекс актуальной документации.
- `docs/DEVELOPMENT_GUIDE.md` — настройка окружения и ежедневная разработка.
- `docs/DATABASE_DESIGN.md` — актуальная схема и назначение таблиц.
- `docs/DATABASE_MANAGEMENT.md` — работа с БД и snapshot/dashboard-потоком.
- `docs/MIGRATION_COMMANDS.md` — команды Alembic и рабочие сценарии.
- `docs/POSTGRESQL_SETUP.md` — запуск PostgreSQL в dev-среде.
- `project_progress/PROJECT_OVERVIEW.md` — краткая карта проекта и навигация.
- `project_progress/PROJECT_PLAN.md` — текущий инженерный план.
- `project_progress/STATUS.md` — текущее состояние и ближайшие задачи.
- `project_progress/SYNC_FLOW.md` — детальный поток синхронизации.
- `project_progress/DEVELOPMENT_JOURNAL.md` — хронология значимых изменений.

## Структура проекта

```text
src/
├── domain/           # Доменные модели и value objects
├── application/      # Парсер Excel, change detector, orchestrator
└── infrastructure/   # БД, воркеры, file_system, scheduler

dashboard/            # Snapshot и HTML dashboard для проверки БД
docs/                 # Актуальная техническая документация
migrations/           # Alembic миграции
project_progress/     # Память проекта: обзор, план, статус, журнал
testing/scripts/      # Проверочные сценарии для ручного прогона
tests/                # Unit и integration тесты
```

## Быстрый старт

### Требования

- Python 3.9+
- Docker
- PostgreSQL 16 через `docker-compose.db.yml`

### 1. Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

Для Windows:

```bash
.venv\Scripts\activate
```

### 2. Поднять PostgreSQL

```bash
docker network create devnet
docker-compose -f docker-compose.db.yml up -d
```

Конфигурация БД по умолчанию уже лежит в `config.env`.

### 3. Применить миграции

```bash
alembic upgrade head
```

### 4. Проверить окружение

```bash
python scripts/test/test_postgres_connection.py
python -m pytest
ruff check .
```

## Конфигурация

В проекте сейчас используются два env-файла:

- `config.env` — читается `DatabaseConfig` и используется для БД, миграций, dashboard-скриптов и
  части проверочных сценариев.
- `.env` — читается `FileSystemConfig` и `SchedulerConfig`.

Минимальный набор для БД в `config.env`:

```env
DB_TYPE=postgresql
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

Если нужен только типовой dev-сценарий, достаточно актуальных значений из `config.env`.

## Проверка синхронизации и БД

Базовые проверки:

```bash
python scripts/test/test_excel_parsing.py
python scripts/test/test_sync_integration.py --sync-type full --log-level INFO
```

Создание snapshot и HTML dashboard:

```bash
python dashboard/create_db_snapshot.py --label manual_check
python dashboard/generate_dashboard.py --mode latest
python dashboard/run_dashboard_check.py --label smoke_check
```

## Архитектурные ориентиры

- DDD со слоями `domain`, `application`, `infrastructure`.
- Источник истории изменений — `event_store`.
- Актуальное состояние для чтения — `read_deals` и `read_positions`.
- Период обработки определяется листами Excel.
- Для `full/partial` sync изменение сделки обрабатывается атомарно на уровне всей сделки через
  `DealWithPositionsCreated`.
- Любое изменение позиции должно поднимать изменение сделки и приводить к полной переписи сделки
  в `read_deals/read_positions`.

## Стандарты разработки

- Язык общения — русский.
- Код, коммиты и docstring — английский.
- Основные правила разработки — `.cursor/rules/ENGINEERING_RULES.md`.
- Целевая бизнес-логика синхронизации — `.cursor/rules/project_goals.md`.
- Линтинг — `ruff check .`.
- Коммиты — Conventional Commits.

## Состояние документации

Актуальными источниками истины считаются документы из разделов `docs/` и `project_progress/`,
на которые есть ссылки в этом файле. Исторические и разовые отчеты вынесены в архивные зоны и не
должны использоваться как каноническое описание текущего поведения системы.
