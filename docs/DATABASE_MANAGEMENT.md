# Управление базой данных

## Обзор

Система использует PostgreSQL 16 с Event Sourcing + CQRS архитектурой. База данных содержит:
- **Event Store** - все изменения данных
- **Read Models** - денормализованные данные для быстрого чтения
- **Audit** - история изменений
- **Statistics** - агрегированные метрики

## Структура базы данных

### Основные таблицы

1. **event_store** - Event Sourcing для всех изменений
2. **read_deals** - Денормализованные данные сделок
3. **read_positions** - Денормализованные данные позиций
4. **read_audit** - Аудит изменений
5. **read_stats** - Статистика и метрики
6. **sync_sessions** - Сессии синхронизации

### Особенности архитектуры

- **Event Sourcing** - все изменения сохраняются как события
- **CQRS** - разделение на команды (запись) и запросы (чтение)
- **Версионность** - автоматическое отслеживание версий
- **Аудит** - полная история изменений
- **Индексы** - оптимизированные индексы для производительности

## Управление

### Запуск PostgreSQL

```bash
# Windows
scripts/services/start_postgresql.bat

# Linux/Mac
docker-compose -f docker-compose.db.yml up -d postgres
```

### Остановка PostgreSQL

```bash
# Windows
scripts/services/stop_postgresql.bat

# Linux/Mac
docker-compose -f docker-compose.db.yml stop postgres
```

### Инициализация базы данных

```bash
# Windows
scripts/services/init_database.bat

# Linux/Mac
python scripts/services/init_database.py
```

### Проверка состояния

```bash
# Windows
scripts/services/check_database.bat

# Linux/Mac
python scripts/services/check_database.py
```

## Миграции

### Применение миграций

```bash
cd migrations
alembic upgrade head
```

### Создание новой миграции

```bash
cd migrations
alembic revision --autogenerate -m "Description of changes"
```

### Откат миграций

```bash
cd migrations
alembic downgrade -1  # Откат на одну версию назад
alembic downgrade base  # Откат к началу
```

## Конфигурация

### Переменные окружения

```env
# Тип базы данных
DB_TYPE=postgresql

# PostgreSQL параметры
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass

# Настройки пула соединений
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Docker Compose

```yaml
services:
  postgres:
    image: postgres:16
    container_name: so_pg
    environment:
      POSTGRES_DB: so_uchet
      POSTGRES_USER: so_user
      POSTGRES_PASSWORD: so_pass
    ports:
      - "5432:5432"
    volumes:
      - so_pg_data:/var/lib/postgresql/data
```

## Мониторинг

### Проверка подключения

```bash
python scripts/services/check_database.py
```

### Логи PostgreSQL

```bash
docker-compose -f docker-compose.db.yml logs postgres
```

### Статистика контейнера

```bash
docker stats so_pg
```

## Резервное копирование

### Создание бэкапа

```bash
docker exec so_pg pg_dump -U so_user so_uchet > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
docker exec -i so_pg psql -U so_user so_uchet < backup_file.sql
```

## Устранение неполадок

### Проблемы с подключением

1. Проверить статус контейнера: `docker-compose -f docker-compose.db.yml ps`
2. Проверить логи: `docker-compose -f docker-compose.db.yml logs postgres`
3. Проверить сеть: `docker network ls`

### Проблемы с миграциями

1. Проверить версию: `alembic current`
2. Проверить историю: `alembic history`
3. Принудительно обновить: `alembic upgrade head --sql`

### Очистка данных

```bash
# Остановить контейнер
docker-compose -f docker-compose.db.yml down

# Удалить volume
docker volume rm service_oper_uchet_so_pg_data

# Запустить заново
docker-compose -f docker-compose.db.yml up -d postgres
```

## Производительность

### Настройки PostgreSQL

```sql
-- Увеличить shared_buffers для кэширования
ALTER SYSTEM SET shared_buffers = '256MB';

-- Настроить work_mem для операций сортировки
ALTER SYSTEM SET work_mem = '4MB';

-- Перезагрузить конфигурацию
SELECT pg_reload_conf();
```

### Мониторинг производительности

```sql
-- Активные соединения
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- Статистика таблиц
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables;

-- Размер таблиц
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public';
```
