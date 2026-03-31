# Host Runtime

## Назначение

Инструкция для запуска проекта на текущей Ubuntu-машине вне devcontainer.

Результат:

- CLI доступен как отдельная команда на хосте;
- ежедневный job запускается через `systemd` в `06:00`;
- последовательность фиксирована: `fetch_excel_from_smb.py` -> `so-uchet sync full` -> `so-uchet snapshot create`;
- выполнение не зависит от открытого терминала или VS Code;
- Python-окружение живёт локально в проекте как `.venv`;
- конфигурация берётся из основного `config.env`;
- логи пишутся в `/var/log/so-uchet/` и ротируются за 7 дней.

## Что добавлено в репозиторий

- `scripts/host/run_host_cli.sh` - wrapper для запуска CLI в локальном `.venv`
- `config.env` - основной runtime-конфиг для запуска с хоста
- `scripts/host/run_daily_fetch_and_sync.sh` - daily pipeline fetch -> sync
- `scripts/host/install_host_runtime.sh` - установка venv, wrapper, systemd timer и logrotate
- `deploy/systemd/so-uchet-daily-sync.service.template`
- `deploy/systemd/so-uchet-daily-sync.timer.template`
- `deploy/logrotate/so-uchet.template`

## Подготовка

### 1. Убедиться, что вы на хосте

Проверьте текущий путь и пользователя:

```bash
pwd
whoami
```

### 2. Проверить системные зависимости

Проверьте наличие необходимых команд:

```bash
python3 --version
python3 -m venv --help >/dev/null
smbclient --version
logrotate --version
docker --version
docker-compose --version
```

Если какой-то команды нет, установите только недостающий пакет. Например:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv smbclient logrotate
```

### 3. Подготовить `config.env`

Для хостового запуска в `config.env` должны быть как минимум:

- `DB_HOST=127.0.0.1`
- `DB_PORT=5432`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `SMB_USERNAME`
- `SMB_PASSWORD`

`DB_HOST=127.0.0.1` нужен для запуска с хоста.

Проверить текущие значения можно так:

```bash
grep -E '^(DB_HOST|DB_PORT|DB_NAME|DB_USER|DB_PASSWORD|SMB_USERNAME|SMB_PASSWORD)=' config.env
```

### 4. Проверить локальное Python-окружение

Если `.venv` уже существует, можно использовать его:

```bash
ls -ld .venv
```

Проверить, установлен ли CLI в окружении:

```bash
./.venv/bin/so-uchet --help
```

Если `.venv` отсутствует или CLI не запускается, installer создаст или обновит окружение.

### 5. Проверить доступность PostgreSQL на хосте

Если БД запущена через `docker-compose.db.yml`, порт уже опубликован как `127.0.0.1:5432`.

Проверьте, слушает ли порт:

```bash
ss -ltn | grep 5432
```

Если порт не слушает, проверьте состояние контейнера:

```bash
docker ps --filter name=so_pg
```

Если контейнер не запущен, поднимите только то, чего не хватает:

```bash
docker network inspect devnet >/dev/null 2>&1 || docker network create devnet
docker-compose -f docker-compose.db.yml up -d
```

## Установка и обновление runtime

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

Проверить, что wrapper создан:

```bash
ls -l /usr/local/bin/so-uchet-host
```

## Ручной запуск CLI

Перед первым включением timer проверьте CLI вручную:

```bash
so-uchet-host db test
so-uchet-host sync status
so-uchet-host sync list --limit 20
```

Подробная инструкция по CLI:

- `docs/CLI_USAGE.md`

Если БД новая или схема могла измениться, сначала проверьте, нужны ли миграции:

```bash
so-uchet-host db migrate
```

Если команда завершается без новых действий или пишет, что всё уже на `head`, дополнительных действий не нужно.

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
3. `so-uchet snapshot create --label daily_YYYYMMDD_HHMMSS --source daily_sync`

Каждый шаг выполняется только при успехе предыдущего (`set -Eeuo pipefail`).
Snapshot создаётся автоматически после успешной синхронизации с меткой `daily_sync`.

## Логи

Основной лог:

```bash
tail -f /var/log/so-uchet/daily-sync.log
```

Статус последнего запуска сервиса:

```bash
systemctl status so-uchet-daily-sync.service
```

Последние записи systemd-журнала:

```bash
journalctl -u so-uchet-daily-sync.service -n 50 --no-pager
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

## Администрирование

Отключить автозапуск:

```bash
sudo systemctl disable --now so-uchet-daily-sync.timer
```

Включить обратно:

```bash
sudo systemctl enable --now so-uchet-daily-sync.timer
```

Перезапустить только разовый job:

```bash
sudo systemctl restart so-uchet-daily-sync.service
```

Обновить runtime после `git pull`:

```bash
source .venv/bin/activate
pip install -e .
sudo ./scripts/host/install_host_runtime.sh --skip-pip-install
```

Если менялись зависимости и нужно обновить `.venv`, не используйте `--skip-pip-install`.

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
so-uchet-host snapshot create --label manual_check
```
