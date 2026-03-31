# CLI Usage

## Назначение

Практическая инструкция по использованию `so-uchet` на хосте.

CLI можно запускать двумя способами:

- напрямую из локального окружения проекта: `./.venv/bin/so-uchet`
- через wrapper после установки host runtime: `so-uchet-host`

Если используется host runtime, `so-uchet-host` автоматически берёт `config.env`.

## Проверка CLI

Проверить, что команда доступна из локального `.venv`:

```bash
./.venv/bin/so-uchet --help
```

Проверить wrapper:

```bash
so-uchet-host --help
```

## Общий формат

Примеры:

```bash
./.venv/bin/so-uchet db test
./.venv/bin/so-uchet sync status
so-uchet-host snapshot list
```

Глобальные опции CLI:

- `--log-level DEBUG|INFO|WARNING|ERROR`
- `--env-file PATH`

Пример с явным env-файлом:

```bash
./.venv/bin/so-uchet --env-file ./config.env db test
```

## Команды `db`

### `db test`

Проверяет подключение к БД.

```bash
so-uchet-host db test
```

Ожидаемый результат:

- при успехе: `Database connection: OK`
- при ошибке: сообщение Click об ошибке подключения

### `db migrate`

Применяет Alembic-миграции до `head`.

```bash
so-uchet-host db migrate
```

Когда использовать:

- после новой установки;
- после `git pull`, если в репозитории появились новые миграции;
- перед первым запуском timer на новой БД.

### `db align`

Проверяет и выравнивает существующую схему под baseline-контракт.

```bash
so-uchet-host db align
so-uchet-host db align --apply-fixes
so-uchet-host db align --apply-fixes --stamp
```

Это команда для администрирования схемы. Используйте её осознанно, если понимаете состояние БД.

## Команды `sync`

### `sync status`

Показывает текущую `pending` sync-session или последнюю завершённую.

```bash
so-uchet-host sync status
```

Полезно для проверки:

- идёт ли синхронизация сейчас;
- не осталась ли зависшая сессия;
- какой файл и когда обрабатывался последним.

### `sync list`

Показывает историю последних sync-сессий.

```bash
so-uchet-host sync list
so-uchet-host sync list --limit 20
```

### `sync full`

Запускает полную синхронизацию по Excel-файлу.

```bash
so-uchet-host sync full --log-level INFO
```

С другим файлом:

```bash
so-uchet-host sync full --file /path/to/file.xlsx --log-level INFO
```

Эта команда меняет состояние БД.

### `sync partial`

Синхронизирует только последние `N` периодов.

```bash
so-uchet-host sync partial --last-periods 3 --log-level INFO
```

Эта команда меняет состояние БД.

### `sync periods`

Синхронизирует только выбранные периоды.

```bash
so-uchet-host sync periods --periods "Январь 2026" --periods "Февраль 2026" --log-level INFO
```

Эта команда меняет состояние БД.

## Команды `snapshot`

### `snapshot create`

Создаёт snapshot базы данных.

```bash
so-uchet-host snapshot create
so-uchet-host snapshot create --label before_sync
so-uchet-host snapshot create --label nightly_check --source manual
```

Команда пишет данные в таблицу snapshot-ов.

### `snapshot list`

Показывает последние snapshot-записи.

```bash
so-uchet-host snapshot list
so-uchet-host snapshot list --limit 50
```

## Команды `dashboard`

### `dashboard latest`

Генерирует dashboard по последнему snapshot.

```bash
so-uchet-host dashboard latest
so-uchet-host dashboard latest --no-browser
```

### `dashboard compare`

Сравнивает два snapshot-а.

```bash
so-uchet-host dashboard compare --label1 before_sync --label2 after_sync --no-browser
so-uchet-host dashboard compare --id1 10 --id2 11 --no-browser
```

### `dashboard excel-health`

Генерирует Excel Health dashboard.

```bash
so-uchet-host dashboard excel-health --no-browser
so-uchet-host dashboard excel-health --file ./data/real_data_for_testing/Data_source_excel.xlsx --periods "Март 2026" --threshold 1000 --no-browser
```

## Типовые сценарии

### Проверка перед nightly sync

```bash
so-uchet-host db test
so-uchet-host sync status
so-uchet-host sync list --limit 5
```

### Ручной запуск sync

```bash
set -a
source ./config.env
set +a
./.venv/bin/python scripts/services/fetch_excel_from_smb.py
so-uchet-host sync full --log-level INFO
```

### Проверка результата после sync

```bash
so-uchet-host sync status
so-uchet-host sync list --limit 10
so-uchet-host snapshot create --label after_manual_sync
```

## Что меняет состояние системы

Команды, которые только читают:

- `db test`
- `sync status`
- `sync list`
- `snapshot list`
- `dashboard latest`
- `dashboard compare`
- `dashboard excel-health`

Команды, которые меняют состояние:

- `db migrate`
- `db align`
- `sync full`
- `sync partial`
- `sync periods`
- `snapshot create`

## Диагностика

Если CLI не запускается:

```bash
ls -l .venv/bin/so-uchet
./.venv/bin/so-uchet --help
```

Если не удаётся подключиться к БД:

```bash
grep -E '^(DB_HOST|DB_PORT|DB_NAME|DB_USER|DB_PASSWORD)=' config.env
ss -ltn | grep 5432
so-uchet-host db test
```

Если nightly sync не стартовал:

```bash
systemctl status so-uchet-daily-sync.timer
systemctl status so-uchet-daily-sync.service
journalctl -u so-uchet-daily-sync.service -n 50 --no-pager
tail -f /var/log/so-uchet/daily-sync.log
```
