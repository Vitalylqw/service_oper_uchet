# ФИНАЛЬНЫЙ АРХИТЕКТУРНЫЙ ПЛАН ПРОЕКТА

**Система синхронизации Excel → PostgreSQL с версионностью**

*Архитектор: Senior Solutions Architect*
*Версия: 1.0 (Final)*
*Дата: 2025-01-XX*

---

## 🎯 АРХИТЕКТУРНАЯ ФИЛОСОФИЯ

**Принцип**: *"Делай проще, но думай о будущем"*

- ✅ **Простота MVP** — быстрый старт с минимальной сложностью
- ✅ **Готовность к росту** — архитектура позволяет масштабирование
- ✅ **Проверенные технологии** — никаких экспериментов в продакшене
- ✅ **Существующий код** — максимальное переиспользование

---

## 📦 СТРУКТУРА ПРОЕКТА

### Моно-репозиторий с четким разделением

```
service_oper_uchet/
├── src/
│   ├── domain/              # 🧠 Предметная область
│   ├── application/         # 📋 Бизнес-логика  
│   ├── infrastructure/      # 🔧 Внешние интеграции
│   └── presentation/        # 🌐 API и UI
├── tests/                   # 🧪 Все виды тестов
├── ops/                     # 🚀 DevOps и мониторинг
├── docs/                    # 📚 Документация
└── scripts/                 # 🛠️ Утилиты
```

---

## 🏗️ КОМПОНЕНТЫ СИСТЕМЫ

### 1. **Domain Layer** (`src/domain/`)

**Назначение**: Чистая бизнес-логика без зависимостей

**Компоненты**:

- `models.py` — Pydantic модели (Deal, DealItem, SyncSession)
- `value_objects.py` — Money, Period, HashKey, Status
- `interfaces.py` — Абстракции репозиториев
- `exceptions.py` — Доменные исключения

**Технологии**: Pydantic v2, Python 3.9+, mypy strict
**Покрытие тестами**: 100%

### 2. **Application Layer** (`src/application/`)

**Назначение**: Сценарии использования (Use Cases)

**Компоненты**:

- `excel_parser/` — **Переработка существующего** `excel_parser.py`
- `change_detector/` — Алгоритмы сравнения данных
- `sync_orchestrator/` — Управление процессом синхронизации
- `data_validator/` — Валидация и сверка с 1С

**Технологии**: pandas, requests (для 1С API)
**Покрытие тестами**: 95% (критичные компоненты)

### 3. **Infrastructure Layer** (`src/infrastructure/`)

**Назначение**: Работа с внешними системами

**Компоненты**:

- `database/` — PostgreSQL, Event Store, Read Models
- `file_system/` — Получение файлов (SMB/FTP/HTTP)
- `scheduler/` — APScheduler + Windows Task Scheduler резерв
- `monitoring/` — Loguru + Prometheus метрики
- `notifications/` — Email алерты

**Технологии**: SQLAlchemy 2.0, Alembic, Redis
**Покрытие тестами**: 85%

### 4. **Presentation Layer** (`src/presentation/`)

**Назначение**: Внешние интерфейсы

**Компоненты**:

- `api/` — FastAPI REST сервис
- `cli/` — Командная строка для админов
- `web/` — React SPA для аналитиков

**Технологии**: FastAPI, React 18 + TypeScript, JWT auth
**Покрытие тестами**: 80%

---

## 🔄 EVENT SOURCING & CQRS

### Event Store

- **Таблица**: `event_store` с JSONB полями
- **Партиции**: По месяцам автоматически
- **Индексы**: GIN по event_data, B-tree по aggregate_id
- **Retention**: 2 года (настраиваемо)

### Read Models

- **`read_deals`** — Оптимизированная выборка сделок
- **`read_positions`** — Позиции товаров с аггрегатами
- **`read_audit`** — История изменений
- **`read_stats`** — Аналитические метрики

### Command/Query Separation

- **Commands** → Event Store → Workers → Read Models
- **Queries** → Read Models (только чтение)

---

## 🚀 DEPLOYMENT АРХИТЕКТУРА

### Production Setup

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   API GW    │    │ Sync Service│    │ PostgreSQL  │
│  (FastAPI)  │◄──►│ + Workers   │◄──►│ + Redis     │
└─────────────┘    └─────────────┘    └─────────────┘
       ▲                    │
       │                    ▼
┌─────────────┐    ┌─────────────┐
│   Web UI    │    │  Monitoring │
│  (React)    │    │ (Prometheus)│
└─────────────┘    └─────────────┘
```

### Контейнеризация

- **Один Docker Compose** для всех сервисов
- **Multi-stage build** для production образов
- **Volumes** для персистентных данных
- **Health checks** для всех сервисов

---

## 📋 ROADMAP РЕАЛИЗАЦИИ

### 🎯 Sprint 0: Фундамент (1 неделя)

**Цель**: Подготовить базовую архитектуру

- [X] Рефакторинг `excel_parser.py` → `src/application/excel_parser/`
- [X] Создание domain моделей на основе существующих классов
- [X] Event Store схема + миграции Alembic
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Базовые integration тесты

**Deliverable**: Парсер работает, события пишутся в БД

### 🏗️ Sprint 1: Core Logic (2 недели)

**Цель**: Основная бизнес-логика

- [ ] Change Detector с хешированием
- [ ] Sync Orchestrator (полная + инкрементальная синхронизация)
- [ ] Read Model Builder (Worker)
- [ ] Базовая валидация данных
- [ ] Scheduler с retry логикой

**Deliverable**: Полный цикл синхронизации работает

### 🌐 Sprint 2: Интерфейсы (2 недели)

**Цель**: API и UI для пользователей

- [ ] FastAPI с основными эндпоинтами
- [ ] JWT аутентификация + RBAC
- [ ] React Dashboard с таблицами
- [ ] Интеграция с 1С API (с мокированием)
- [ ] Email уведомления

**Deliverable**: Пользователи могут работать с системой

### 🎛️ Sprint 3: Production Ready (1 неделя)

**Цель**: Готовность к продакшену

- [ ] Monitoring stack (Prometheus + Grafana)
- [ ] Полные integration тесты
- [ ] Performance тестирование
- [ ] Security hardening
- [ ] Backup процедуры

**Deliverable**: Система готова к production

### 📈 Sprint 4: Optimization (1 неделя)

**Цель**: Финальная полировка

- [ ] Оптимизация БД запросов
- [ ] Advanced фильтры в UI
- [ ] Детальная аналитика
- [ ] Документация пользователя
- [ ] SLA мониторинг

**Deliverable**: GA готовый продукт

---

## 🛠️ ТЕХНОЛОГИЧЕСКИЙ СТЕК

### Backend

- **Python 3.9+** — основной язык
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** — ORM
- **Pydantic v2** — валидация данных
- **pandas** — обработка Excel
- **Redis** — кеш и очереди
- **Loguru** — структурированное логирование

### Frontend

- **React 18** — UI фреймворк
- **TypeScript** — типизация
- **Vite** — build tool
- **ECharts** — графики
- **TanStack Query** — state management

### Infrastructure

- **PostgreSQL 16** — основная БД
- **Docker + Compose** — контейнеризация
- **Prometheus + Grafana** — мониторинг
- **GitHub Actions** — CI/CD

### Quality Assurance

- **pytest** — тестирование
- **ruff** — линтер
- **mypy** — type checker
- **black** — форматтер

---

## 📊 КРИТЕРИИ УСПЕХА

### MVP (Sprint 1)

- ✅ Ежедневная синхронизация без участия человека
- ✅ Обнаружение 100% изменений в данных
- ✅ Сохранение полной истории версий
- ✅ Основные REST API работают

### Production (Sprint 3)

- ✅ Синхронизация 1000 сделок за < 5 минут
- ✅ API отвечает за < 2 секунды
- ✅ Покрытие тестами > 90%
- ✅ Zero-downtime deployment

### Business Ready (Sprint 4)

- ✅ Интеграция с 1С функционирует
- ✅ Web UI интуитивно понятен пользователям
- ✅ Система алертов настроена
- ✅ Документация готова

---

## ⚡ КЛЮЧЕВЫЕ РЕШЕНИЯ

### 1. **Переиспользование существующего кода**

`excel_parser.py` уже хорошо написан — рефакторим в application layer

### 2. **Моно-репозиторий для MVP**

Упрощает DevOps, ускоряет разработку, снижает overhead

### 3. **Event Sourcing + Read Models**

Обеспечивает требования по версионности без потери производительности

### 4. **Прагматичная CQRS**

Разделение команд и запросов без фанатизма

### 5. **Готовность к масштабированию**

Архитектура позволяет выделить сервисы при росте нагрузки

---

## 🎯 NEXT STEPS

1. **Утверждение плана** — финализация архитектурных решений
2. **Team Setup** — назначение ролей и ответственности
3. **Environment** — настройка dev/staging окружений
4. **Sprint 0 Kickoff** — начало реализации

---

*Создано с учетом лучших практик Enterprise Architecture и реальных потребностей бизнеса.*

**Ключевой принцип**: *Архитектура должна служить бизнесу, а не наоборот.*
