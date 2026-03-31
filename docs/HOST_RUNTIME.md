# Host Runtime

## Назначение

Инструкция для запуска проекта на текущей Ubuntu-машине вне devcontainer.

Результат:

- CLI доступен как отдельная команда на хосте;
- ежедневный job запускается через `systemd` в `06:00`;
- последовательность фиксирована: `fetch_excel_from_smb.py` -> `so-uchet sync full`;
- выполнение не зависит от открытого терминала или VS Code;
- Python-окружение живёт локально в проекте как `.venv`;
- конфигурация берётся из основного `config.env`;
- логи пишутся в `/var/log/so-uchet/` и ротируются за 7 дней.

## Что добавлено в репозиторий

- `scripts/host/run_host_cli.sh` - wrapper для запуска CLI в host-venv
- `config.env` - основной runtime-конфиг для запуска с хоста
- `scripts/host/run_daily_fetch_and_sync.sh` - daily pipeline fetch -> sync
- `scripts/host/install_host_runtime.sh` - установка venv, wrapper, systemd timer и logrotate
- `deploy/systemd/so-uchet-daily-sync.service.template`
- `deploy/systemd/so-uchet-daily-sync.timer.template`
- `deploy/logrotate/so-uchet.template`

## Подготовка

### 1. Подготовить `config.env`

Для хостового запуска в `config.env` должны быть как минимум:

- `DB_HOST=127.0.0.1`
- `DB_PORT=5432`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `SMB_USERNAME`
- `SMB_PASSWORD`

`DB_HOST=127.0.0.1` нужен для запуска с хоста.

### 2. Проверить доступность PostgreSQL на хосте

Если БД запущена через `docker-compose.db.yml`, порт уже опубликован как `127.0.0.1:5432`.

### 3. Проверить наличие `smbclient`

```bash
sudo apt-get update
sudo apt-get install -y smbclient
```

## Установка host runtime

```bash
sudo ./scripts/host/install_host_runtime.sh
```

Что делает installer:

- создаёт или использует локальный virtualenv `.venv`;
- устанавливает проект в editable-режиме;
- создаёт wrapper `/usr/local/bin/so-uchet-host`;
- разворачивает `systemd` unit и timer;
- включает timer;
- создаёт `/var/log/so-uchet`;
- разворачивает `logrotate` с retention 7 дней.

## Ручной запуск CLI

```bash
so-uchet-host db test
so-uchet-host sync status
so-uchet-host sync list --limit 20
```

Если нужен другой env-файл или другой venv, можно переопределить:

```bash
SO_UCHET_ENV_FILE=/path/to/config.env SO_UCHET_VENV=/path/to/venv so-uchet-host db test
```

## Управление расписанием

Проверить timer:

```bash
systemctl status so-uchet-daily-sync.timer
systemctl list-timers so-uchet-daily-sync.timer
```

Ручной запуск job:

```bash
sudo systemctl start so-uchet-daily-sync.service
```

По умолчанию сервис делает:

1. `python scripts/services/fetch_excel_from_smb.py`
2. `so-uchet sync full --log-level INFO`

Если `fetch` завершился с ошибкой, синхронизация не запускается.

## Логи

Основной лог:

```bash
tail -f /var/log/so-uchet/daily-sync.log
```

Ротация:

- ежедневно;
- хранение 7 архивов;
- сжатие старых логов;
- `copytruncate`, чтобы не зависеть от перезапуска timer/service.

Проверка конфигурации:

```bash
sudo logrotate -d /etc/logrotate.d/so-uchet
```

## Важный operational risk

Текущий `sync` runtime уже помечен в проекте как потенциально нестабильный на реальном объёме данных: есть инцидент с долгим выполнением partial/full sync и историей зависшей `pending` session.

Что сделано в host runtime для снижения риска:

- `systemd` останавливает job через `SIGINT`, а не через стандартный `SIGTERM`;
- shell-wrapper прокидывает сигнал дочернему процессу;
- это помогает текущему CLI корректно закрывать `pending` session при штатной остановке сервиса.

Что это не решает полностью:

- внезапное убийство процесса `SIGKILL`;
- crash машины;
- существующую проблему, если сам sync зависает или не укладывается в ожидания по runtime.

Поэтому перед постоянной эксплуатацией разумно сделать минимум один ручной прогон:

```bash
so-uchet-host db test
python scripts/services/fetch_excel_from_smb.py
so-uchet-host sync full --log-level INFO
```
