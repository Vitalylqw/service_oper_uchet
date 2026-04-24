# Статус проекта

## Цель

Поддерживать корректную синхронизацию Excel -> event_store -> read models и иметь воспроизводимые
инструменты проверки результата через тесты и dashboard.

## Актуальное состояние

Завершено и активно используется:

- DDD-структура `domain` / `application` / `infrastructure`;
- Excel parser;
- change detection на основе hash-comparison;
- event store и обработка событий в read-модели;
- упрощенная синхронизация позиций без `is_active/version`;
- трассировка строк Excel через nullable `source_row_number` в read-моделях;
- snapshot/dashboard-контур для проверки целостности БД;
- unit и integration тесты в `tests/`.

В разработке:

- CLI-обёртка `so-uchet` — частично реализованная единая точка входа:
  `db` и `sync` уже есть, `snapshot/dashboard` ещё по плану `plans/STAGE-CLI.md`.
- согласован этап проектирования поиска по PostgreSQL read-side:
  `plans/STAGE-SEARCH.md`.

Не является активной частью проекта:
- REST API;
- UI;
- 1С-интеграция как рабочий контур.

## Что сделано недавно

### 2026-04-24

- реализована source-row traceability для поиска сделок в Excel и сортировки отчетов
  в порядке исходного файла;
- принято проектное решение: `source_row_number` не входит в `deal_key` и бизнес-`hash_key`;
- добавлен отдельный read-side refresh для номеров строк, чтобы массовый сдвиг строк не создавал
  `DealWithPositionsCreated` для всех сделок периода;
- первая миграция оставляет `source_row_number` nullable и без unique constraint, а ошибки
  уникальности/отсутствия строки фиксируются как warnings и в отчетах.
- добавлена миграция `0004_add_source_row_numbers.py`: поля `source_row_number` в
  `read_deals` и `read_positions`, плюс неуникальные индексы для поиска/сортировки;
- обновлены parser, domain models, read-model builders, repositories и dashboard/audit reports,
  чтобы номер строки проходил от Excel до отчетов;
- контрольный sync по периоду `Апрель 2026` подтвердил заполнение:
  `641/641` сделок и `3405/3405` позиций имеют `source_row_number`, дублей строк не найдено.

## Памятка по проверке и частые ловушки

Этот блок нужен как рабочая памятка, чтобы не повторять ошибки, обнаруженные при реализации
`source_row_number`.

### Запуск sync

Правильный CLI-запуск точечной синхронизации:

```bash
PYTHONPATH=src ./.venv/bin/so-uchet --log-level INFO sync periods \
  --file data/real_data_for_testing/Data_source_excel.xlsx \
  --periods "Апрель 2026" \
  --log-level INFO
```

Не использовать для проверки sync:

```bash
PYTHONPATH=src ./.venv/bin/python -m cli.main sync periods ...
```

Причина: `src/cli/main.py` сейчас не содержит прямой точки запуска вида
`if __name__ == "__main__": cli()`, поэтому команда через `python -m cli.main ...` может
завершиться без реального выполнения Click-команды.

### Проверки после sync

После контрольной синхронизации source-row обязательно проверять БД, а не только лог:

```sql
select 'deals' as table_name, count(*) as total, count(source_row_number) as with_source_row
from read_deals
where period_month = 'Апрель' and period_year = '2026'
union all
select 'positions', count(*), count(source_row_number)
from read_positions
where period_month = 'Апрель' and period_year = '2026';
```

И отдельно проверять дубли:

```sql
with deal_dups as (
    select source_row_number
    from read_deals
    where period_month = 'Апрель'
      and period_year = '2026'
      and source_row_number is not null
    group by source_row_number
    having count(*) > 1
),
position_dups as (
    select deal_key, source_row_number
    from read_positions
    where period_month = 'Апрель'
      and period_year = '2026'
      and source_row_number is not null
    group by deal_key, source_row_number
    having count(*) > 1
)
select
    (select count(*) from deal_dups) as duplicate_deal_rows,
    (select count(*) from position_dups) as duplicate_position_rows;
```

### PostgreSQL / asyncpg bulk `VALUES`

При bulk `UPDATE ... FROM (VALUES ...)` через `asyncpg` нельзя полагаться на автоматический вывод
типов для смешанных текстовых и integer-полей.

Ошибки, на которые уже наткнулись:

- `operator does not exist: integer = text`;
- `invalid input for query argument ... expected str, got int`.

Для PostgreSQL-ветки `SourceLocationRefresher` integer metadata-поля (`position_number`,
`source_row_number`) передаются стабильно и приводятся в SQL через `::integer`. Если менять этот код,
нужно проверять именно реальным PostgreSQL sync, потому что unit-тесты на mock/session такие ошибки
типизации не ловят.

### Имена полей в change detection

У `ChangeDetectionResult` правильные свойства:

- `insertion_count`;
- `update_count`;
- `deletion_count`;
- списки `insertions`, `updates`, `deletions`.

Неправильно:

- `insertions_count`;
- `updates_count`;
- `result.changes`.

### Текущая известная неидемпотентность

Повторный sync по `Апрель 2026` может показывать `~641 updates`. Диагностика показала, что причина
не в `source_row_number`, а в существующей нормализации бизнес-данных:

- пример `upd_number`: `None -> ""`;
- расхождения точности позиции после записи/чтения БД, например Excel `338.37736` против
  read-model `338.38000`.

Это отдельный вопрос бизнес-правил точности и сравнения. Его нельзя исправлять как часть
source-row traceability без отдельного решения по финансовому округлению.

### Локальные ограничения команд

В sandbox прямой `psql` к локальному PostgreSQL может падать с:

```text
Operation not permitted
```

Это не обязательно ошибка БД. Для такой проверки нужен разрешенный запуск команды в окружении с
доступом к локальному сокету/порту PostgreSQL.

Полный `tests/unit` на момент этой записи упирался в несвязанный legacy-тест
`tests/unit/test_cli_db.py::test_load_runtime_env_promotes_legacy_db_variables`
из-за отсутствующего `_DOTENV_LOADED` в `src.cli.common`. Для проверки source-row изменения
использовался:

```bash
./.venv/bin/python -m pytest -q tests/unit --ignore=tests/unit/test_cli_db.py
```

### 2026-04-02

- проведена проверка готовности живой БД к поиску по `read_deals` / `read_positions`;
- подтверждено, что PostgreSQL уже содержит конфигурацию `russian`, но в active schema
  отсутствуют `GIN`-индексы и текущий поиск опирается на `ILIKE`;
- подтверждено, что основные поисковые сценарии сосредоточены вокруг клиента, организации,
  поставщика, номенклатуры, периода и счета;
- зафиксирован отдельный этап `plans/STAGE-SEARCH.md` с минималистичным и надежным подходом:
  структурные индексы + FTS без `pg_trgm` в первом релизе;
- в stage-план включено измерение влияния новых индексов на ночную batch-синхронизацию
  и post-sync `ANALYZE`.
- добавлена и применена migration `0003_add_read_side_search_indexes.py` с обязательными
  индексами для `read_deals` / `read_positions`;
- подтверждено через `EXPLAIN ANALYZE`, что новые btree- и GIN-индексы реально используются;
- репозиторный поиск переведён на PostgreSQL FTS + структурные условия с fallback для
  non-PostgreSQL окружений;
- вынесен общий loader `config.env` в `src/infrastructure/config/env_loader.py`;
- `connection.py` переведён на единый runtime-путь загрузки `config.env`, без изменения формата
  самого файла;
- подтверждено, что `DatabaseConfig()` теперь читает реальные PostgreSQL-параметры из
  `config.env`, raw `asyncpg` подключение работает, а `search_deals()` проходит end-to-end
  через async PostgreSQL runtime.
- по `sync_sessions` зафиксирован узкий baseline для production-like full sync:
  `9` прогонов за `2026-03-31` - `2026-04-02`, диапазон `623` - `739` сек, среднее
  `656.7` сек;
- выполнен первый контролируемый post-change full sync через `so-uchet`:
  `767.79` сек, что даёт примерно `+16.9%` к среднему baseline и `+3.9%` к его верхней границе;
- подтверждено, что рост времени sync есть, но на текущем объёме данных он пока остаётся
  приемлемым для ночного batch-сценария;
- отдельно зафиксировано, что для устойчивого вывода желательно ещё `1-2` повторных замера.

### 2026-03-30

- active docs повторно сверены с кодом, миграциями и структурой репозитория;
- зафиксировано, что `so-uchet` уже содержит рабочие группы `db` и `sync`, но ещё не покрывает
  `snapshot/dashboard`;
- migration-story уточнена под фактическую active history: `0001_baseline_current_schema.py` +
  `0002_drop_read_audit.py`;
- ссылки на `.cursor/...` и `testing/scripts/` вычищены из active docs в пользу `.agents/...` и
  `scripts/test/`.

### 2026-03-14

- спроектирована CLI-обёртка `so-uchet` (фреймворк: `click`, расположение: `src/cli/`);
- создан детальный план из 5 подэтапов: `plans/STAGE-CLI.md`;
- обновлена проектная документация: `PROJECT_PLAN.md`, `STATUS.md`, `PROJECT_OVERVIEW.md`,
  `DEVELOPMENT_JOURNAL.md`.

### 2026-03-08

- начата полная ревизия документации;
- активные документы приводятся к инженерному формату;
- historical документы подготавливаются к переносу в архивные зоны.
- ручные проверочные сценарии нормализуются в `scripts/test/` вместо `testing/scripts/`;
- конфликт Alembic history с дублированным `revision = "0003"` устранён через переход на baseline
  `0001` с последующей active-миграцией `0002_drop_read_audit.py`;
- старая цепочка `0001..0005` вынесена в архив `migrations/archive/versions_pre_baseline_20260308/`;
- добавлен сервисный сценарий `scripts/services/align_existing_db_to_baseline.py` для проверки,
  выравнивания известных drift-расхождений и `stamp` существующей БД.
- после дополнительной проверки runtime-логики snapshot восстановлен контракт
  `db_snapshots.created_at DEFAULT now()` в БД, baseline, модели и align-скрипте.
- выполнена сверка фактических runtime-импортов и SQLAlchemy driver usage с
  `requirements.txt`/`pyproject.toml`;
- в manifests зависимостей добавлены подтверждённые runtime-пакеты
  `python-dotenv`, `APScheduler`, `xlcalculator`;
- из `pyproject.toml` удалён `redis`, так как текущее прямое использование в проекте не
  подтверждено.
- подтверждено, что `read_audit` не используется в рабочем runtime и не наполняется;
- вывод `read_audit` из целевой архитектуры вынесен в отдельный DDL-шаг, который теперь
  представлен active-миграцией `0002_drop_read_audit.py`.

### 2026-03-07

- из проекта удалены UI и API;
- документация должна отражать только sync-core и dashboard-инструменты.

### 2026-03-06

- усилен parser: безопасный decimal parsing;
- добавлены валидаторы обрезки строк в доменных моделях;
- расширены unit-тесты.

### 2026-02-28

- добавлен DB dashboard и snapshot-таблицы;
- восстановлена синхронизация после регрессии контракта `Deal/DealItem`;
- усилен интеграционный сценарий проверки sync flow.

## Текущие рабочие задачи

- развить CLI-обёртку `so-uchet` по плану `plans/STAGE-CLI.md`: после реализованных `db` и `sync`
  закрыть `snapshot/dashboard` и финализацию;
- выполнить этап `plans/STAGE-SEARCH.md`: сначала PostgreSQL-индексы и контракт поиска,
  затем ещё `1-2` контрольных замера производительности и документирование фактического эффекта;
- завершить актуализацию документации и архивирование historical files;
- зафиксировать канонические документы проекта;
- проверить поведение `has_totals_error` для сценариев с `NULL` totals;
- после полной пересинхронизации проверить качество заполнения `source_row_number` и решить,
  нужна ли вторая миграция с `NOT NULL`/unique constraints;
- проверить причину избыточного количества событий в `event_store` в отдельных сценариях;
- при необходимости расширить drift-check для других legacy-инстансов PostgreSQL.
- проверить legacy upgrade path после уже добавленной миграции `0002_drop_read_audit.py`.

## Риски и ограничения

- часть старых документов содержит полезную архитектурную память, но уже не описывает текущее
  поведение;
- в проекте есть конфигурационная неоднозначность между `config.env` и `.env`;
- единый loader для `config.env` уже вынесен в infrastructure и подключён в DB runtime, но
  общая конфигурационная модель проекта по-прежнему разделена между `config.env` и `.env`;
- существующие БД, оставшиеся на старой схеме без baseline-`stamp`, будут показывать невалидную
  Alembic-версию до выполнения сценария выравнивания и последующего апгрейда до `head`;
- при выборе канонической схемы для технических таблиц нельзя опираться только на `models.py`:
  нужно проверять реальный путь записи данных;
- `project_progress/SYNC_FLOW.md` раньше отставал от реального кода, поэтому его нужно читать
  только в актуализированной версии;
- в legacy-БД `read_audit` ещё может присутствовать до применения отдельной миграции удаления.
- поисковый этап нельзя расширять до fuzzy search и `pg_trgm` до базовых замеров времени sync
  и проверки реальных пользовательских сценариев.
- `source_row_number` пока является диагностическим nullable-полем; жесткие DB constraints
  откладываются до проверки реальных данных после полной пересинхронизации.

## Что дальше

Ближайший приоритет:

1. довести CLI-обёртку `so-uchet` до полного плана Этапа B;
2. реализовать согласованный этап поиска по `plans/STAGE-SEARCH.md`;
3. довести документацию до состояния `active docs + archive`;
4. после этого отдельно разобрать открытые вопросы по качеству синхронизации;
5. затем определить, нужен ли отдельный этап по полной унификации конфигурации окружения.
