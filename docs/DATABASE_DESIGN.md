# Архитектура базы данных

## Назначение

База данных поддерживает два контура:

- history/write-side через `event_store`;
- current/read-side через `read_deals` и `read_positions`.

Дополнительно в схеме есть технические таблицы для агрегатов, статистики и snapshot-контроля.

## Основная схема

```text
Excel
  -> event_store
  -> read_deals
  -> read_positions
  -> read_stats
  -> db_snapshots
```

## Ключевые таблицы

### `event_store`

Назначение:

- хранить историю событий синхронизации;
- обеспечивать последовательную обработку через `sequence_number`;
- позволять повторно строить read-модели.

Ключевые поля:

- `event_id`
- `aggregate_id`
- `aggregate_type`
- `event_type`
- `event_data`
- `event_metadata`
- `sequence_number`
- `processed_at`

Особенности:

- события одной сделки упорядочиваются по `(aggregate_id, sequence_number)`;
- необработанные события определяются как `processed_at IS NULL`.

### `read_deals`

Назначение:

- хранить актуальное состояние сделки в денормализованном виде;
- держать declared totals и calculated totals рядом.

Ключевые поля:

- идентификация: `id`, `deal_key`, `hash_key`
- период: `period_month`, `period_year`, `period_full_name`
- статусы: `is_shipped`, `is_paid`
- totals из Excel:
  - `total_revenue_amount`
  - `total_margin_amount`
  - `total_cost_amount`
  - `kickback_amount_value`
- calculated totals:
  - `calc_revenue_amount`
  - `calc_margin_amount`
  - `calc_cost_amount`
- quality flags:
  - `has_totals_error`
- агрегаты:
  - `items_count`
  - `total_quantity`

### `read_positions`

Назначение:

- хранить текущее состояние позиций сделки;
- давать быстрый read-side для анализа и сверки.

Ключевые поля:

- `id`
- `deal_id`
- `deal_key`
- `position_number`
- `hash_key`
- `product_name`
- `supplier_name`
- `quantity`
- `purchase_price_amount`
- `sale_price_amount`
- `revenue_amount`
- `margin_amount`
- `cost_amount`

Ограничения:

- `hash_key` уникален;
- `(deal_id, position_number)` уникальны;
- `deal_id` связан с `read_deals` через `ON DELETE CASCADE`.

Текущее проектное решение:

- таблица не использует `is_active` и `version`;
- хранится только актуальное состояние позиции;
- история изменений уходит в `event_store`.

### `sync_sessions`

Назначение:

- фиксировать факты запусков синхронизации;
- хранить статус, путь к файлу, размеры, время и ошибки.

### Historical note: `read_audit`

Ранее в схеме и коде существовал отдельный read-side аудит `read_audit`.

Текущее решение:

- история изменений хранится только в `event_store`;
- отдельная таблица `read_audit` признана лишней для текущего atomic sync flow;
- active schema удаляет её отдельной миграцией `0002_drop_read_audit.py`, при этом в legacy-БД
  таблица может сохраняться до применения `alembic upgrade head`.

### `read_stats`

Назначение по схеме:

- хранить агрегированную статистику по типу, дате и измерению.

Фактический нюанс:

- таблица и модель существуют;
- обновление реализовано через обработку `SyncSessionCompleted`;
- нужно отдельно проверять, попадает ли такой event в текущий runtime path.

### `db_snapshots`

Назначение:

- хранить контрольные снимки состояния `read_deals` и `read_positions`;
- использоваться dashboard-скриптами для сравнения до/после.

Связанные таблицы:

- `db_snapshot_deal_periods`
- `db_snapshot_position_periods`

Они содержат детализацию snapshot-метрик по периодам.

## Точность денежных полей

### `read_deals`

- `total_*` и `calc_*` хранятся как `NUMERIC(15, 2)`.

### `read_positions`

- `purchase_price_amount` — `NUMERIC(18, 5)`
- `margin_amount` — `NUMERIC(18, 5)`
- `sale_price_amount`, `revenue_amount`, `cost_amount` — `NUMERIC(15, 2)`
- `quantity` — `NUMERIC(15, 3)`

Это соответствует текущей модели проекта: повышенная точность нужна не для всех сумм, а только для
части полей позиции.

## Поддерживаемые БД

Код модели поддерживает:

- PostgreSQL как основной рабочий вариант;
- SQLite как fallback для части dev/test сценариев.

Это обеспечивается обертками `GUID` и `JSONType` в `src/infrastructure/database/models.py`.

## Что важно помнить

- каноническая схема определяется не этим документом, а комбинацией:
  - `src/infrastructure/database/models.py`
  - `migrations/versions/*.py`
- старые описания схемы с `users`, API-layer или versioned read positions не считаются актуальными;
- перед изменением схемы нужно обновлять и миграции, и активную документацию.
