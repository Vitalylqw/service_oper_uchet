# Руководство разработчика

## Назначение

Этот документ описывает рабочий dev-поток для текущего scope проекта: sync-core, БД, тесты,
dashboard и миграции.

Если нужен общий обзор проекта, сначала откройте:

- `../README.md`
- `../project_progress/PROJECT_OVERVIEW.md`
- `../project_progress/SYNC_FLOW.md`

## Требования

- Python 3.9+
- Docker
- PostgreSQL 16 через `docker-compose.db.yml`

Проверка базовых инструментов:

```bash
python --version
docker --version
```

## Установка зависимостей

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

## Конфигурация

### Что используется сейчас

- `config.env` — база данных, миграции, dashboard и многие runtime-скрипты.
- `.env` — `FileSystemConfig` и `SchedulerConfig`.

Для типовой локальной разработки достаточно актуального `config.env`.

Минимальный набор DB-параметров:

```env
DB_TYPE=postgresql
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

## Поднятие БД

```bash
docker network create devnet
docker-compose -f docker-compose.db.yml up -d
alembic upgrade head
```

Если БД уже поднята, достаточно повторно выполнить `alembic upgrade head`.

## Тесты и проверки

### Основные команды

```bash
python -m pytest
python -m pytest -m "unit"
python -m pytest -m "integration"
ruff check .
mypy src/
```

### Проверочные сценарии

```bash
python scripts/test/test_postgres_connection.py
python scripts/test/test_excel_parsing.py
python scripts/test/test_sync_integration.py --sync-type full --log-level INFO
python scripts/test/test_sync_integration.py --sync-type partial --log-level DEBUG
```

### Что проверять после sync

Минимальные SQL-проверки:

```sql
SELECT COUNT(*) FROM read_deals;
SELECT COUNT(*) FROM read_positions;
SELECT event_type, COUNT(*) FROM event_store GROUP BY event_type;
SELECT COUNT(*) FROM read_deals WHERE has_totals_error = true;
```

## Dashboard и snapshot-поток

Для быстрой верификации состояния БД:

```bash
python dashboard/create_db_snapshot.py --label before_test
python dashboard/generate_dashboard.py --mode latest
python dashboard/run_dashboard_check.py --label smoke_check
```

HTML dashboard теперь разбивает длинные периодные таблицы на страницы по 15 строк.
Это относится к блокам `Deals by Period`, `Positions by Period` и `Cross-compare`.
Строка общего `TOTAL` в периодных таблицах не участвует в пагинации и остаётся видимой
на любой странице.

Сценарий до/после:

```bash
python dashboard/run_dashboard_check.py --before sync_case
python scripts/test/test_sync_integration.py --sync-type partial --log-level INFO
python dashboard/run_dashboard_check.py --after sync_case
```

## Миграции

Базовые команды:

```bash
alembic current
alembic history
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "Describe change"
```

Сейчас активная история Alembic состоит из одной baseline-миграции. Исторические ревизии вынесены в
архив и не являются рабочим путём обновления.

Для существующей БД используйте:

```bash
python scripts/services/align_existing_db_to_baseline.py
python scripts/services/align_existing_db_to_baseline.py --apply-known-fixes --stamp
```

Подробные сценарии вынесены в `MIGRATION_COMMANDS.md`.

## Обновление Excel-файла с SMB-шары

Скрипт `scripts/services/fetch_excel_from_smb.py` автоматизирует получение актуального
Excel-файла с сетевой шары, удаление ненужного листа "Отчеты" и конвертацию `.xlsm` → `.xlsx`.

Требования: `smbclient` (`sudo apt install smbclient`).

```bash
# Через переменные среды (рекомендуется — пароль не попадает в историю shell)
SMB_USERNAME=Vitaly SMB_PASSWORD='...' python scripts/services/fetch_excel_from_smb.py

# Через аргументы
python scripts/services/fetch_excel_from_smb.py --username Vitaly --password '...'
```

Что делает скрипт:

1. Скачивает `ОперативныйУчет.xlsm` с `\\192.168.1.3\Share\Учет`.
2. Удаляет лист "Отчеты" и VBA-макросы (ZIP-level, без загрузки в openpyxl).
3. Создаёт бэкап в `data/real_data_for_testing/backups/` (ротация: макс. 15 файлов).
4. Сохраняет результат как `data/real_data_for_testing/Data_source_excel.xlsx`.
5. Верифицирует результат через openpyxl.

Дополнительные флаги: `--no-backup`, `--skip-verify`, `--exclude-sheets`, `--host`, `--share`,
`--remote-path`. Подробности: `python scripts/services/fetch_excel_from_smb.py --help`.

## Правила разработки

- соблюдать `.cursor/rules/ENGINEERING_RULES.md`;
- не менять существующее поведение без прямой необходимости;
- проверять гипотезы до утверждений;
- держать документацию синхронной с кодом;
- использовать `ruff` как основной линтер;
- писать commit messages в формате Conventional Commits.

## Практические ориентиры по коду

- `src/application/excel_parser/parser.py` — parsing.
- `src/application/change_detector/detector.py` — comparison logic.
- `src/application/sync_orchestrator/orchestrator.py` — orchestration.
- `src/infrastructure/workers/read_model_builder.py` — application of events.
- `src/infrastructure/workers/simple_position_sync.py` — atomic rewrite of deal positions.
- `src/infrastructure/database/models.py` — DB schema in code.

## Текущие технические нюансы

- основной runtime-поток использует deal-level event `DealWithPositionsCreated`;
- old model с `is_active/version` больше не считается рабочим описанием;
- history/write-side поддерживается только через `event_store`;
- `read_audit` выведен из целевой архитектуры и удаляется отдельной миграцией;
- `read_stats` не следует считать автоматически заполненным на каждом запуске без отдельной проверки
  event path.

## Когда обновлять документацию

Документацию нужно обновлять, если меняется хотя бы одно из следующего:

- sync flow;
- схема БД;
- команда запуска или проверочный сценарий;
- расположение ключевых файлов;
- договоренность о канонических документах проекта.
