# Обзор проекта

## Назначение

`Service Oper Uchet` синхронизирует данные из Excel-книги с базой данных и строит read-модели для
быстрого чтения и проверки результата. Целевое поведение и ограничения зафиксированы в
`project_goals.md`.

Главный результат работы системы:

- изменения из Excel фиксируются в `event_store`;
- текущее состояние сделок хранится в `read_deals`;
- текущее состояние позиций хранится в `read_positions`;
- дополнительные агрегаты и техконтроль поддерживаются через `read_stats` и `db_snapshots`.

## Текущий scope

В активном scope:

- Excel parser;
- change detection;
- event store;
- read model builder;
- dashboard и snapshot-скрипты для контроля целостности;
- unit/integration тесты;
- CLI-обёртка `so-uchet` в частично реализованном состоянии: группы `db` и `sync` уже есть,
  `snapshot/dashboard` остаются в отдельных скриптах.

Вне активного scope:

- REST API;
- UI;
- 1С-интеграция;
- пользовательская auth-модель.

## Архитектура

- `src/domain/` — доменные модели, value objects, исключения, интерфейсы.
- `src/application/` — прикладные сервисы: Excel parser, change detector, sync orchestrator.
- `src/infrastructure/` — БД, воркеры, scheduler, file system.

Ключевые точки:

- `src/application/excel_parser/parser.py` — парсинг Excel.
- `src/application/change_detector/detector.py` — сравнение Excel и текущего состояния БД.
- `src/application/sync_orchestrator/orchestrator.py` — общий orchestration flow.
- `src/infrastructure/database/models.py` — SQLAlchemy модели.
- `src/infrastructure/workers/read_model_builder.py` — применение событий к read-моделям.
- `src/infrastructure/workers/simple_position_sync.py` — упрощенная синхронизация позиций.
- `src/cli/` — CLI-обёртка `so-uchet` (presentation layer, сейчас реализованы `db` и `sync`).

## Поток данных

```text
Excel file
  -> ExcelParserService
  -> ChangeDetectorService
  -> event_store
  -> ReadModelBuilder
  -> read_deals / read_positions / read_stats
  -> db_snapshots / HTML dashboards
```

## Навигация по репозиторию

```text
dashboard/             # snapshot и dashboard-проверки
docs/                  # актуальная документация
migrations/            # Alembic миграции
plans/                 # детальные планы этапов
project_progress/      # обзор, план, статус, журнал, sync flow
scripts/test/          # ручные проверочные сценарии и bat-обертки
src/cli/               # CLI-обёртка so-uchet (`db` и `sync`; без snapshot/dashboard)
tests/                 # unit и integration тесты
```

## Конфигурация

Текущее состояние конфигурации:

- `config.env` — основная конфигурация БД.
- `.env` — настройки `file_system` и `scheduler`.

Это неидеально и должно учитываться при запуске скриптов: dashboard, миграции и БД ориентируются
на `config.env`.

## Что открыть в первую очередь

Для входа в проект:

1. `README.md`
2. `project_progress/PROJECT_PLAN.md`
3. `project_progress/STATUS.md`
4. `project_progress/SYNC_FLOW.md`
5. `docs/DEVELOPMENT_GUIDE.md`

## Принципы разработки

- DDD и минимальные изменения в существующем поведении.
- Проверка гипотез до утверждений.
- Документация должна быть инженерной, а не маркетинговой.
- История решений сохраняется, но historical docs не должны подменять active docs.
