# Ubuntu setup

## Назначение

Краткая памятка для запуска проекта на Ubuntu или внутри dev-container.

## Требования

- Ubuntu 20.04+
- Docker
- Python 3.9+

## Базовый запуск

### 1. Установить зависимости Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 2. Поднять PostgreSQL

```bash
docker network create devnet
docker-compose -f docker-compose.db.yml up -d
```

### 3. Применить миграции

```bash
alembic upgrade head
```

### 4. Проверить БД

```bash
python scripts/test/test_postgres_connection.py
```

## Проверка sync flow

```bash
python scripts/test/test_excel_parsing.py
python scripts/test/test_sync_integration.py --sync-type full --log-level INFO
```

## Запуск на хост-машине вне devcontainer

Для постоянного запуска на текущей Ubuntu-машине добавлена отдельная host-обвязка:

- локальный virtualenv проекта `.venv`
- wrapper-команда `so-uchet-host`
- `systemd` timer на 06:00
- file logging в `/var/log/so-uchet/`
- `logrotate` с retention 7 дней

Краткий сценарий:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
sudo apt-get install -y python3-venv smbclient logrotate
sudo ./scripts/host/install_host_runtime.sh
so-uchet-host db test
systemctl status so-uchet-daily-sync.timer
```

Подробная инструкция:

- `docs/HOST_RUNTIME.md`

## Snapshot и dashboard

```bash
python dashboard/create_db_snapshot.py --label ubuntu_check
python dashboard/generate_dashboard.py --mode latest
```

## Остановка

```bash
docker-compose -f docker-compose.db.yml down
```

## Что важно

- для БД проект ориентируется на `config.env`;
- этот файл не описывает UI/API, потому что они не входят в текущий scope проекта;
- подробные инструкции по разработке находятся в `docs/DEVELOPMENT_GUIDE.md`.
