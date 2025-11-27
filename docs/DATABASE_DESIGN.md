# 🗄️ АРХИТЕКТУРА БАЗЫ ДАННЫХ SERVICE_OPER_UCHET

> **Версия**: 1.1  
> **Дата обновления**: 27 ноября 2025  
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

### Основные таблицы (обновлено)

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
-- Read Models (CQRS)
CREATE TABLE read_deals (
    id UUID PRIMARY KEY,
    deal_key VARCHAR(255) UNIQUE NOT NULL,
    hash_key CHAR(32) NOT NULL,
    client_name VARCHAR(500) NOT NULL,
    invoice_info VARCHAR(500) NOT NULL,
    invoice_number VARCHAR(100),
    invoice_date VARCHAR(20),
    period_month VARCHAR(20) NOT NULL,
    period_year  VARCHAR(4)  NOT NULL,
    period_full_name VARCHAR(100) NOT NULL,
    is_shipped VARCHAR(20),
    is_paid    VARCHAR(20),
    upd_number VARCHAR(100),
    seller     VARCHAR(300),
    total_revenue_amount NUMERIC(15,2),
    total_margin_amount  NUMERIC(15,2),
    total_cost_amount    NUMERIC(15,2),
    kickback_amount_value NUMERIC(15,2),
    calc_revenue_amount NUMERIC(15,2) DEFAULT 0 NOT NULL,
    calc_margin_amount  NUMERIC(15,2) DEFAULT 0 NOT NULL,
    calc_cost_amount    NUMERIC(15,2) DEFAULT 0 NOT NULL,
    has_totals_error    BOOLEAN DEFAULT FALSE NOT NULL,
    items_count   INTEGER DEFAULT 0 NOT NULL,
    total_quantity NUMERIC(15,3),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE read_positions (
    id UUID PRIMARY KEY,
    deal_id UUID NOT NULL REFERENCES read_deals(id) ON DELETE CASCADE,
    deal_key VARCHAR(255) NOT NULL,
    position_number INTEGER NOT NULL,
    hash_key CHAR(32) NOT NULL,
    product_name VARCHAR(1000) NOT NULL,
    supplier_name VARCHAR(500),
    pickup_date   VARCHAR(50),
    quantity NUMERIC(15,3),
    purchase_price_amount NUMERIC(18,5),  -- Changed to 5 decimal places precision
    sale_price_amount     NUMERIC(15,2),
    revenue_amount        NUMERIC(15,2),
    margin_amount         NUMERIC(18,5),  -- Changed to 5 decimal places precision
    cost_amount           NUMERIC(15,2),
    client_name VARCHAR(500) NOT NULL,
    period_month VARCHAR(20) NOT NULL,
    period_year  VARCHAR(4)  NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(deal_id, position_number)
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

## 💰 ТИПЫ ДАННЫХ И ТОЧНОСТЬ

### Денежные поля с разной точностью

Система использует разные типы точности для различных денежных полей:

| Поле | Тип в БД | Точность | Value Object | Использование |
|------|----------|----------|--------------|---------------|
| `purchase_price_amount` | `NUMERIC(18,5)` | 5 знаков | `Money5` | Цена закупки в DealItem |
| `margin_amount` | `NUMERIC(18,5)` | 5 знаков | `SignedMoney5` | Маржа в DealItem |
| `sale_price_amount` | `NUMERIC(15,2)` | 2 знака | `Money` | Цена продажи |
| `revenue_amount` | `NUMERIC(15,2)` | 2 знака | `Money` | Выручка |
| `cost_amount` | `NUMERIC(15,2)` | 2 знака | `Money` | Стоимость закупки |
| `total_revenue_amount` | `NUMERIC(15,2)` | 2 знака | `Money` | Общая выручка по сделке |
| `total_margin_amount` | `NUMERIC(15,2)` | 2 знака | `SignedMoney` | Общая маржа по сделке |

**Примечание:** Поля `purchase_price_amount` и `margin_amount` имеют повышенную точность (5 знаков) для более точных расчетов и сохранения исходной точности из Excel файлов.

### Value Objects

В доменном слое используются следующие value objects:

- **Money** - положительные денежные суммы с точностью 2 знака
- **Money5** - положительные денежные суммы с точностью 5 знаков (для `purchase_price`)
- **SignedMoney** - денежные суммы (могут быть отрицательными) с точностью 2 знака
- **SignedMoney5** - денежные суммы (могут быть отрицательными) с точностью 5 знаков (для `margin`)

## 📖 READ MODELS (CQRS)

### Принцип работы

Read Models - это **денормализованные представления** дан