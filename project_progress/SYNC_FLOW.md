Процесс синхронизации данных от Excel до read-моделей

## Цель

Зафиксировать текущую реализацию sync flow по коду, а не по устаревшим описаниям.

Главная задача процесса:

- распарсить Excel;
- определить отличия от текущего состояния БД;
- записать изменения в `event_store`;
- привести `read_deals` и `read_positions` к актуальному состоянию;
- дать возможность проверить результат через snapshot/dashboard и тесты.

## Точка входа

- основной runtime-вход: `SyncOrchestratorService.execute_sync(file_path, config)`;
- проверочный сценарий: `scripts/test/test_sync_integration.py`.

## Основные участники

- `ExcelParserService` — превращает Excel в `Deal` и `DealItem`.
- `ChangeDetectorService` — сравнивает Excel-данные с текущим состоянием БД.
- `SyncOrchestratorService` — управляет фазами синхронизации.
- `EventStoreImplementation` — записывает события в `event_store`.
- `ReadModelBuilder` — применяет события к read-моделям.
- `SimplePositionSync` — выполняет атомарную перепись сделки и ее позиций.

## Текущая модель обработки

Ключевой момент текущей реализации:

- и `full`, и `partial` проходят через фазу `detect_changes`;
- оркестратор в рабочем пути создает события через `_create_incremental_sync_events()`;
- фактический основной event format для вставки и обновления сделки — `DealWithPositionsCreated`;
- удаление сделки оформляется как `DealDeleted`.

Это означает, что текущий рабочий путь ориентирован на атомарную обработку сделки целиком, а не на
отдельные события по позициям как основной сценарий.

## Пошаговый сценарий

### 1. Создание sync session

`SyncOrchestratorService`:

- генерирует `session_id`;
- проверяет, что нет другой running session;
- создает `SyncSession`;
- заполняет метаданные исходного файла;
- сохраняет запись в `sync_sessions`.

Результат:

- в БД есть активная сессия синхронизации;
- файл и его хэш зафиксированы на уровне сессии.

### 2. Парсинг Excel

`ExcelParserService.parse_file(file_path, sync_session)`:

- читает листы книги;
- извлекает период из имени листа;
- строит `Deal` и вложенные `DealItem`;
- проставляет `source_row_number` из абсолютного номера строки Excel для сделки и позиции;
- собирает статистику парсинга.

Результат:

- формируется `ParseResult`;
- у оркестратора есть `deals`, `file_hash`, `file_size`, counters по сделкам и позициям.

### 3. Detect changes

`ChangeDetectorService.detect_changes(excel_deals, sync_period_months=0)`:

- загружает сделки из БД для периодов, присутствующих в Excel;
- считает change hash на уровне сделки;
- находит insert, update, delete;
- для update дополнительно формирует `field_changes`.

Что важно:

- сравнение идет по `deal_key` для сделок;
- hash сделки учитывает и сами позиции внутри сделки;
- любое изменение позиции в рабочем sync path должно поднимать `deal UPDATE`;
- удаление определяется как отсутствие сущности из Excel в текущей выборке БД по тем же периодам.
- `source_row_number` не участвует в бизнес-сравнении: перенос строки в Excel сам по себе
  не должен создавать событие изменения сделки.

Результат:

- оркестратор получает `ChangeDetectionResult`.

### 4. Генерация событий

Текущий рабочий путь использует `_create_incremental_sync_events()`:

- `deal INSERT` -> `DealWithPositionsCreated`
- `deal UPDATE` -> `DealWithPositionsCreated`
- `deal DELETE` -> `DealDeleted`

Содержимое `DealWithPositionsCreated`:

- `event_data.deal` — все поля сделки;
- `event_data.items` — все позиции сделки;
- `source_row_number` — диагностическое поле source-location для сделки и каждой позиции;
- `metadata` — `sync_session_id`, `sync_type`, `change_type`, `source`.

Отдельный метод `_create_full_sync_events()` в коде есть, но `execute_sync()` в текущем пути его не
использует.

### 5. Запись в event store

`EventStoreImplementation.append_events(events)`:

- определяет `aggregate_type`;
- рассчитывает `sequence_number` внутри `aggregate_id`;
- пишет события в `event_store`;
- новые события остаются с `processed_at IS NULL`.

Результат:

- события сохранены как источник истории изменений;
- они готовы к обработке `ReadModelBuilder`.

### 6. Обновление read-моделей

`ReadModelBuilder.process_latest_events(limit=1_000_000, auto_commit=True)`:

- забирает необработанные события;
- сортирует их по `(aggregate_id, sequence_number)`;
- обрабатывает каждое событие в отдельном `SAVEPOINT`;
- после успешной обработки проставляет `processed_at`.

Поддерживаемые deal-события:

- `DealCreated` -> upsert в `read_deals`;
- `DealWithPositionsCreated` -> атомарная синхронизация сделки и всех позиций;
- `DealUpdated` -> обновление отдельных полей сделки;
- `DealDeleted` -> жесткое удаление сделки и ее позиций.

Поддерживаемые item-события в `ReadModelBuilder` есть, но основной orchestrator-path их не создает.
Главный runtime-контракт сейчас такой: изменение позиции должно проявиться как изменение сделки
и привести к `DealWithPositionsCreated`.

### 7. Атомарная синхронизация сделки

`ReadModelBuilder._sync_deal_with_positions()`:

- собирает `Deal` из payload события;
- передает сделку в `SimplePositionSync.sync_deal_positions(...)`;
- `SimplePositionSync` выполняет полную перепись сделки и ее позиций;
- затем вызывается `_recalculate_totals(deal.id)`.

Смысл этой ветки:

- изменение сделки трактуется как изменение сделки целиком;
- позиции не версионируются;
- старый подход с `is_active/version` больше не является рабочей моделью.

### 7.1. Refresh source row metadata

После обработки событий read-моделей выполняется отдельный read-side refresh номеров строк Excel.

Зачем это выделено отдельно:

- номер строки нужен для поиска в Excel и сортировки отчетов;
- номер строки не является бизнес-идентичностью сделки;
- массовый сдвиг строк в Excel не должен создавать `DealWithPositionsCreated` для всех сделок периода.

Текущий контракт:

- `source_row_number` не входит в `deal_key`;
- `source_row_number` не входит в бизнес-`hash_key`;
- изменение только `source_row_number` не создает business `UPDATE`;
- `SourceLocationRefresher` обновляет только `read_deals.source_row_number` и
  `read_positions.source_row_number` bulk-операциями;
- ошибки качества source-row metadata фиксируются как warnings и в отчетах, но не останавливают sync.

Для PostgreSQL refresh использует chunked bulk `UPDATE ... FROM (VALUES ...)`.
Для fallback/dev-сценариев используется generic update по строкам.

Практическая проверка после изменения этого участка должна включать реальный PostgreSQL sync хотя бы
по одному периоду. Mock/unit-тесты не ловят все ошибки типизации `asyncpg` в bulk `VALUES`.
Критичные симптомы, которые уже встречались:

- `operator does not exist: integer = text`;
- `invalid input for query argument ... expected str, got int`.

Контрольный признак успешного refresh в логе:

```text
Source row refresh completed: ... warnings=0
```

После этого нужно проверить заполненность и дубли `source_row_number` прямым SQL по
`read_deals`/`read_positions`.

### 8. Пересчет агрегатов сделки

`_recalculate_totals(deal_id)`:

- считает количество позиций;
- суммирует `quantity`, `revenue_amount`, `margin_amount`, `cost_amount`;
- сравнивает calculated totals с declared totals из `read_deals`;
- обновляет:
  - `items_count`;
  - `total_quantity`;
  - `calc_revenue_amount`;
  - `calc_margin_amount`;
  - `calc_cost_amount`;
  - `has_totals_error`.

### 9. Завершение sync session

`SyncOrchestratorService._complete_sync_session(...)`:

- переводит `SyncSession` в `completed` или `failed`;
- сохраняет итоговый статус через repository.

Результат:

- `sync_sessions` содержит факт прогона;
- read-модели и `event_store` отражают результат обработки.

### 10. Автоматический snapshot после синхронизации

При ежедневном запуске через systemd (`run_daily_fetch_and_sync.sh`), после успешного
завершения sync автоматически создаётся DB snapshot:

- вызывается `so-uchet snapshot create --label daily_YYYYMMDD_HHMMSS --source daily_sync`;
- snapshot фиксирует агрегированные метрики `read_deals` и `read_positions`;
- результат сохраняется в таблицу `db_snapshots`;
- snapshot создаётся только при успехе синхронизации.

Это позволяет:

- отслеживать динамику данных день ко дню;
- сравнивать snapshot-ы через `dashboard compare`;
- быстро обнаруживать аномалии после sync.

## Что хранится в результате

- `sync_sessions` — история запусков синхронизации;
- `event_store` — история событий;
- `read_deals` — актуальные сделки;
- `read_positions` — актуальные позиции;
- `db_snapshots` и дочерние таблицы — контрольные снимки БД для dashboard.

## Важные текущие нюансы

### 0. Проверять sync нужно через `so-uchet`

Для ручной проверки использовать CLI entrypoint:

```bash
PYTHONPATH=src ./.venv/bin/so-uchet --log-level INFO sync periods \
  --file data/real_data_for_testing/Data_source_excel.xlsx \
  --periods "Апрель 2026" \
  --log-level INFO
```

Команда вида `python -m cli.main sync periods ...` не является надежной проверкой, потому что
`cli.main` сейчас не запускает Click-приложение напрямую при вызове через `-m`.

### 1. Основной поток уже не использует old versioning model

Старые описания с `is_active`, `version`, soft-delete для `read_positions` не соответствуют
текущей целевой логике проекта и основному пути обработки.

### 2. `read_audit` выведен из целевой архитектуры

После проверки runtime принято текущее проектное решение:

- история изменений хранится только в `event_store`;
- отдельный read-side аудит `read_audit` не используется в основном потоке;
- cleanup кода и удаление legacy-таблицы были вынесены в отдельные шаги;
- active history Alembic уже содержит миграцию `0002_drop_read_audit.py`, но в legacy-БД таблица
  может присутствовать до применения `alembic upgrade head`.

### 3. `read_stats` поддерживается частично

`ReadModelBuilder` умеет обрабатывать `SyncSessionCompleted`, но основной orchestrator-путь
не создает такие события в `event_store`. Поэтому `read_stats` не следует считать главным итогом
каждого запуска без отдельной проверки сценария.

### 4. Deferred queue оперативная

`DeferredEventQueue` хранится в памяти процесса. Это значит:

- deferred events переживают только текущий процесс;
- при завершении процесса очередь теряется;
- это нужно учитывать при разовых и тестовых прогонах.

## Практическая проверка результата

После sync обычно проверяются:

- количество строк в `read_deals` и `read_positions`;
- количество и типы событий в `event_store`;
- флаг `has_totals_error`;
- наличие и дубли `source_row_number` в рамках периодов/сделок;
- snapshot/dashboard отчеты из `dashboard/`.

Рабочие сценарии:

- `python scripts/test/test_sync_integration.py --sync-type full --log-level INFO`
- `python dashboard/create_db_snapshot.py --label before_check`
- `python dashboard/generate_dashboard.py --mode latest`
