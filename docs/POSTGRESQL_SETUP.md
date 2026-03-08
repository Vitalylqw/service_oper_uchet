# PostgreSQL setup

## Назначение

Проект использует PostgreSQL контейнер `so_pg` в сети `devnet` как основной dev/runtime-вариант.

## Текущая конфигурация

База данных описана в:

- `docker-compose.db.yml`
- `config.env`

Минимальные параметры в `config.env`:

```env
DB_TYPE=postgresql
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

## Первый запуск

Создать сеть:

```bash
docker network create devnet
```

Поднять контейнер:

```bash
docker-compose -f docker-compose.db.yml up -d
```

Применить миграции:

```bash
alembic upgrade head
```

Проверить подключение:

```bash
python scripts/test/test_postgres_connection.py
```

## Повседневные команды

Статус:

```bash
docker-compose -f docker-compose.db.yml ps
```

Логи:

```bash
docker-compose -f docker-compose.db.yml logs postgres
```

Остановка:

```bash
docker-compose -f docker-compose.db.yml stop postgres
```

Полное выключение:

```bash
docker-compose -f docker-compose.db.yml down
```

## Проверка рабочего контура

После поднятия PostgreSQL полезно выполнить:

```bash
python scripts/test/test_postgres_connection.py
python -m pytest -m "integration"
```

Если нужно проверить sync flow поверх поднятой БД:

```bash
python scripts/test/test_sync_integration.py --sync-type full --log-level INFO
```

## Troubleshooting

### `Connection refused`

Проверьте:

- контейнер запущен;
- порт `5432` проброшен;
- сеть `devnet` существует.

Команды:

```bash
docker-compose -f docker-compose.db.yml ps
docker network ls
docker-compose -f docker-compose.db.yml logs postgres
```

### `Host not found`

Обычно означает одну из проблем:

- не создана сеть `devnet`;
- контейнер `so_pg` не поднят;
- `DB_HOST` в `config.env` не совпадает с именем контейнера.

### `Authentication failed`

Проверьте значения:

- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

в `config.env` и `docker-compose.db.yml`.

## Ограничения

- текущие значения в `config.env` являются dev-ориентированными;
- этот документ не описывает production hardening;
- если конфигурация окружения будет переработана, сначала нужно проверить код, который сейчас
  читает именно `config.env`.
