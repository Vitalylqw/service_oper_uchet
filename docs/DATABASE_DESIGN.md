# 🗄️ АРХИТЕКТУРА БАЗЫ ДАННЫХ SERVICE_OPER_UCHET

> **Версия**: 1.0  
> **Дата обновления**: 27 января 2025  
> **Архитектура**: Event Sourcing + CQRS  
> **Поддерживаемые БД**: PostgreSQL, SQLite

---

## 🎯 ОБЗОР АРХИТЕКТУРЫ

Система использует **Event Sourcing** и **CQRS** (Command Query Responsibility Segregation) для обеспечения:

- 🔄 **Полной истории изменений** - все изменения сохраняются как события
- ⚡ **Высокой производительности** - разделение операций чтения и записи
- 📊 **Аналитики и отчетности** - денормализованные read models
- 🔍 **Аудита и трассировки** - полная история всех операций

### Архитектурные принципы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Event Store   │    │  Read Models    │    │   API Layer     │
│   (Write Side)  │    │   (Read Side)   │    │  (Presentation) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Domain        │    │   Read Model    │    │   FastAPI       │
│   Events        │    │   Builder       │    │   Endpoints     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📊 СХЕМА БАЗЫ ДАННЫХ

### Основные таблицы

```sql
-- Event Store (Event Sourcing)
CREATE TABLE event_store (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Read Models (CQRS)
CREATE TABLE deal_read_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id VARCHAR(100) UNIQUE NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    invoice_number VARCHAR(100) NOT NULL,
    invoice_date DATE NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    margin DECIMAL(15,2) NOT NULL,
    seller VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE deal_item_read_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(15,2) NOT NULL,
    total_price DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deal_id) REFERENCES deal_read_model(deal_id)
);

-- Sync Sessions
CREATE TABLE sync_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    file_size INTEGER,
    total_deals INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    errors JSONB,
    warnings JSONB
);

-- Users (для аутентификации)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

---

## 🔄 EVENT STORE (EVENT SOURCING)

### Принцип работы

Event Store является **единственным источником истины** для всех изменений в системе. Каждое изменение сохраняется как событие с полной информацией о том, что произошло.

### Структура событий

```json
{
  "event_type": "DealCreated",
  "aggregate_id": "DEAL-2025-001",
  "event_data": {
    "deal_id": "DEAL-2025-001",
    "client_name": "ООО Рога и Копыта",
    "invoice_number": "INV-2025-001",
    "invoice_date": "2025-01-15",
    "revenue": 150000.00,
    "margin": 45000.00,
    "seller": "Иванов И.И.",
    "items": [
      {
        "product_name": "Товар 1",
        "quantity": 10,
        "unit_price": 15000.00,
        "total_price": 150000.00
      }
    ]
  },
  "created_at": "2025-01-27T10:30:00Z",
  "version": 1
}
```

### Типы событий

| Тип события | Описание | Данные |
|-------------|----------|--------|
| `DealCreated` | Создана новая сделка | Полные данные сделки |
| `DealUpdated` | Обновлена существующая сделка | Измененные поля |
| `DealDeleted` | Удалена сделка | ID сделки |
| `DealItemAdded` | Добавлен товар к сделке | Данные товара |
| `DealItemUpdated` | Обновлен товар в сделке | Измененные поля товара |
| `DealItemDeleted` | Удален товар из сделки | ID товара |
| `SyncSessionStarted` | Начата сессия синхронизации | Данные сессии |
| `SyncSessionCompleted` | Завершена сессия синхронизации | Результаты |
| `SyncSessionFailed` | Ошибка в сессии синхронизации | Детали ошибки |

### Преимущества Event Sourcing

- 🔍 **Полная история** - можно восстановить состояние на любой момент времени
- 📊 **Аналитика** - анализ паттернов изменений
- 🔄 **Воспроизведение** - возможность переиграть события
- 🛡️ **Аудит** - полная трассировка всех изменений
- 🔧 **Отладка** - детальная информация о проблемах

---

## 📖 READ MODELS (CQRS)

### Принцип работы

Read Models - это **денормализованные представления** данных, оптимизированные для быстрого чтения и отображения в UI.

### Структура read models

#### deal_read_model
```sql
-- Основная информация о сделках
SELECT 
    deal_id,
    client_name,
    invoice_number,
    invoice_date,
    revenue,
    margin,
    seller,
    created_at,
    updated_at
FROM deal_read_model
WHERE client_name LIKE '%ООО%'
ORDER BY invoice_date DESC;
```

#### deal_item_read_model
```sql
-- Детали товаров в сделках
SELECT 
    deal_id,
    product_name,
    quantity,
    unit_price,
    total_price
FROM deal_item_read_model
WHERE deal_id = 'DEAL-2025-001';
```

### Преимущества CQRS

- ⚡ **Высокая производительность** - оптимизированные запросы
- 📊 **Гибкость** - разные представления для разных задач
- 🔧 **Масштабируемость** - независимое масштабирование read/write
- 🎯 **Специализация** - оптимизация под конкретные use cases

---

## 🔄 READ MODEL BUILDER

### Принцип работы

Read Model Builder - это **фоновый процесс**, который слушает события из Event Store и обновляет read models.

```python
class ReadModelBuilder:
    async def handle_deal_created(self, event: DealCreated):
        # Создание записи в deal_read_model
        await self.create_deal_read_model(event.data)
        
        # Создание записей в deal_item_read_model
        for item in event.data.items:
            await self.create_deal_item_read_model(event.data.deal_id, item)
    
    async def handle_deal_updated(self, event: DealUpdated):
        # Обновление записи в deal_read_model
        await self.update_deal_read_model(event.data)
```

### Процесс обновления

1. **Событие записано** в Event Store
2. **Read Model Builder** получает уведомление
3. **Обработка события** согласно бизнес-логике
4. **Обновление read models** в транзакции
5. **Подтверждение обработки**

---

## 🔐 СИНХРОНИЗАЦИЯ И СЕССИИ

### Структура sync_sessions

```sql
-- Информация о сессиях синхронизации
SELECT 
    session_id,
    status,
    file_name,
    file_size,
    total_deals,
    total_items,
    created_at,
    completed_at,
    duration_seconds
FROM sync_sessions
WHERE status = 'completed'
ORDER BY created_at DESC;
```

### Статусы сессий

| Статус | Описание |
|--------|----------|
| `pending` | Ожидает обработки |
| `running` | В процессе обработки |
| `completed` | Успешно завершена |
| `failed` | Завершена с ошибкой |
| `cancelled` | Отменена пользователем |

### Обработка ошибок

```json
{
  "errors": [
    {
      "row": 15,
      "column": "invoice_date",
      "message": "Неверный формат даты",
      "value": "2025-13-45"
    }
  ],
  "warnings": [
    {
      "row": 20,
      "column": "revenue",
      "message": "Сумма не совпадает с позициями",
      "expected": 150000.00,
      "actual": 149950.00
    }
  ]
}
```

---

## 👥 АУТЕНТИФИКАЦИЯ И АВТОРИЗАЦИЯ

### Структура users

```sql
-- Пользователи системы
SELECT 
    username,
    role,
    is_active,
    created_at,
    last_login
FROM users
WHERE is_active = TRUE;
```

### Роли и разрешения

| Роль | Разрешения | Описание |
|------|------------|----------|
| `viewer` | `read:deals`, `read:sessions` | Только просмотр |
| `analyst` | `read:deals`, `read:sessions`, `write:sync` | Просмотр + загрузка |
| `admin` | Все разрешения | Полный доступ |

---

## 📈 ИНДЕКСЫ И ОПТИМИЗАЦИЯ

### Основные индексы

```sql
-- Event Store
CREATE INDEX idx_event_store_aggregate_id ON event_store(aggregate_id);
CREATE INDEX idx_event_store_event_type ON event_store(event_type);
CREATE INDEX idx_event_store_created_at ON event_store(created_at);

-- Read Models
CREATE INDEX idx_deal_read_model_client_name ON deal_read_model(client_name);
CREATE INDEX idx_deal_read_model_seller ON deal_read_model(seller);
CREATE INDEX idx_deal_read_model_invoice_date ON deal_read_model(invoice_date);
CREATE INDEX idx_deal_read_model_revenue ON deal_read_model(revenue);

-- Sync Sessions
CREATE INDEX idx_sync_sessions_status ON sync_sessions(status);
CREATE INDEX idx_sync_sessions_created_at ON sync_sessions(created_at);

-- Users
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
```

### Партиционирование (для больших объемов)

```sql
-- Партиционирование по дате (PostgreSQL)
CREATE TABLE deal_read_model_2025_01 PARTITION OF deal_read_model
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE deal_read_model_2025_02 PARTITION OF deal_read_model
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

---

## 🔧 МИГРАЦИИ И ВЕРСИОНИРОВАНИЕ

### Alembic миграции

```python
# Пример миграции
"""Add invoice_date index

Revision ID: 001
Revises: 
Create Date: 2025-01-27 10:30:00

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_index('idx_deal_read_model_invoice_date', 
                   'deal_read_model', ['invoice_date'])

def downgrade():
    op.drop_index('idx_deal_read_model_invoice_date', 
                 'deal_read_model')
```

### Версионирование схемы

- **Major version** - несовместимые изменения
- **Minor version** - новые функции, обратная совместимость
- **Patch version** - исправления ошибок

---

## 🛡️ БЕЗОПАСНОСТЬ

### Шифрование данных

```sql
-- Хеширование паролей (bcrypt)
UPDATE users 
SET password_hash = crypt('new_password', gen_salt('bf'))
WHERE username = 'admin';

-- Проверка пароля
SELECT username 
FROM users 
WHERE username = 'admin' 
  AND password_hash = crypt('password', password_hash);
```

### Аудит и логирование

```sql
-- Аудит изменений
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100),
    table_name VARCHAR(100),
    record_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📊 МОНИТОРИНГ И МЕТРИКИ

### Ключевые метрики

```sql
-- Размер базы данных
SELECT 
    pg_size_pretty(pg_database_size('service_oper_uchet')) as db_size;

-- Количество событий по типам
SELECT 
    event_type,
    COUNT(*) as count
FROM event_store
GROUP BY event_type
ORDER BY count DESC;

-- Производительность запросов
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
WHERE query LIKE '%deal_read_model%'
ORDER BY total_time DESC;
```

### Health checks

```sql
-- Проверка состояния БД
SELECT 
    'event_store' as table_name,
    COUNT(*) as record_count,
    MAX(created_at) as last_event
FROM event_store
UNION ALL
SELECT 
    'deal_read_model' as table_name,
    COUNT(*) as record_count,
    MAX(updated_at) as last_event
FROM deal_read_model;
```

---

## 🔄 РЕЗЕРВНОЕ КОПИРОВАНИЕ

### Стратегия бэкапов

```bash
# Полный бэкап (еженедельно)
pg_dump service_oper_uchet > backup_full_$(date +%Y%m%d).sql

# Инкрементальный бэкап (ежедневно)
pg_dump --data-only --table=event_store service_oper_uchet > backup_events_$(date +%Y%m%d).sql

# Восстановление
psql service_oper_uchet < backup_full_20250127.sql
```

### Репликация

```sql
-- Настройка реплики (PostgreSQL)
-- Primary
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_segments = 64;

-- Replica
ALTER SYSTEM SET hot_standby = on;
```

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

### Скрипты и утилиты

- **[scripts/database/create_schema.py](../scripts/database/create_schema.py)** - создание схемы БД
- **[scripts/database/init_database.py](../scripts/database/init_database.py)** - инициализация данных
- **[src/infrastructure/database/](../src/infrastructure/database/)** - модели и репозитории

### Документация

- **[API Documentation](API_DOCUMENTATION.md)** - REST API
- **[User Guide](USER_GUIDE.md)** - руководство пользователя
- **[Project Documentation](PROJECT_DOCUMENTATION_MASTER.md)** - общая документация

---

**Версия документации**: 1.0  
**Дата обновления**: 27 января 2025  
**Архитектура**: Event Sourcing + CQRS 