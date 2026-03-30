# Управление базой данных

## Назначение

Этот документ описывает практическую работу с PostgreSQL в рамках текущего dev-потока проекта:

- поднятие контейнера;
- применение миграций;
- базовые проверки;
- snapshot/dashboard сценарии;
- резервное копирование и диагностика.

## Запуск PostgreSQL

Создать сеть один раз:

```bash
docker network create devnet
```

Поднять контейнер:

```bash
docker-compose -f docker-compose.db.yml up -d
```

Остановить контейнер:

```bash
docker-compose -f docker-compose.db.yml stop postgres
```

Полностью остановить compose:

```bash
docker-compose -f docker-compose.db.yml down
```

## Конфигурация

Основная DB-конфигурация читается из `config.env`.

Минимально важные поля:

```env
DB_TYPE=postgresql
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

Важно:

- `DatabaseConfig` сейчас использует `config.env`;
- часть других подсистем использует `.env`;
- для операций с БД, миграциями и dashboard ориентируйтесь именно на `config.env`.

## Проверка состояния

Проверка подключения:

```bash
python scripts/test/test_postgres_connection.py
```

Проверка состояния контейнера:

```bash
docker-compose -f docker-compose.db.yml ps
docker-compose -f docker-compose.db.yml logs postgres
```

## Миграции

Применить все миграции:

```bash
alembic upgrade head
```

Посмотреть текущую версию:

```bash
alembic current -v
```

История миграций:

```bash
alembic history --verbose
```

Текущее правило:

- активная история содержит две рабочие ревизии: `0001_baseline_current_schema.py` и
  `0002_drop_read_audit.py`;
- старая цепочка хранится только в архиве `migrations/archive/versions_pre_baseline_20260308/`;
- existing DB нужно сначала проверить, затем `stamp`-ить baseline и после этого доводить до `head`.

Проверка и привязка существующей БД:

```bash
python scripts/services/align_existing_db_to_baseline.py
python scripts/services/align_existing_db_to_baseline.py --apply-known-fixes --stamp
```

## Базовые SQL-проверки

После sync полезно смотреть:

```sql
SELECT COUNT(*) FROM event_store;
SELECT COUNT(*) FROM read_deals;
SELECT COUNT(*) FROM read_positions;
SELECT COUNT(*) FROM read_deals WHERE has_totals_error = true;
SELECT event_type, COUNT(*) FROM event_store GROUP BY event_type ORDER BY event_type;
```

Если нужно понять состояние snapshot-контуров:

```sql
SELECT id, label, source, created_at
FROM db_snapshots
ORDER BY created_at DESC
LIMIT 20;
```

## Snapshot и dashboard

Создать snapshot:

```bash
python dashboard/create_db_snapshot.py --label manual_check
```

Сгенерировать dashboard:

```bash
python dashboard/generate_dashboard.py --mode latest
```

Сравнение до/после:

```bash
python dashboard/run_dashboard_check.py --before sync_case
python dashboard/run_dashboard_check.py --after sync_case
```

Назначение этих инструментов:

- быстро увидеть расхождения `read_deals` vs `read_positions`;
- проверить totals и quantity;
- получить drill-down по периодам и проблемным сделкам.

Особенность HTML dashboard:

- длинные периодные таблицы разбиваются на страницы по 15 строк;
- пагинация применяется к `Deals by Period`, `Positions by Period` и
  `Cross-compare: Deals vs Positions by Period`;
- строка общего `TOTAL` в таблицах периодов остаётся общей по всей таблице и не
  зависит от выбранной страницы.

## Резервное копирование

Создание бэкапа:

```bash
docker exec so_pg pg_dump -U so_user so_uchet > backup_$(date +%Y%m%d_%H%M%S).sql
```

Восстановление:

```bash
docker exec -i so_pg psql -U so_user so_uchet < backup_file.sql
```

## Полная очистка dev-БД

Использовать только если точно нужно пересоздать окружение:

```bash
docker-compose -f docker-compose.db.yml down
docker volume rm service_oper_uchet_so_pg_data
docker-compose -f docker-compose.db.yml up -d
alembic upgrade head
```

## Нюансы текущей схемы

- `read_positions` хранит только текущее состояние и не использует `is_active/version`;
- `event_store` является единственным рабочим источником истории изменений;
- `read_audit` уже удалён из active schema миграцией `0002`, но ещё может присутствовать в
  legacy-БД до применения `alembic upgrade head`;
- `read_stats` нужно оценивать по текущему event path, а не по старым документам;
- `db_snapshots` — это не боевые данные, а технический слой наблюдаемости и проверки.

## Когда смотреть этот документ

Используйте этот файл, если вам нужно:

- поднять БД;
- быстро проверить состояние данных;
- сделать snapshot перед экспериментом;
- понять, какие SQL-проверки являются базовыми для текущего проекта.
