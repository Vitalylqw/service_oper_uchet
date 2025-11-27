# 📚 ДОКУМЕНТАЦИЯ ПРОЕКТА SERVICE_OPER_UCHET

> **Статус проекта**: ✅ PRODUCTION READY  
> **Версия**: 0.2.0 (Sprint 2.3 Real Integration)  
> **Дата обновления**: 27 января 2025  
> **Архитектура**: DDD + Event Sourcing + CQRS

---

## 🎯 ОБЗОР ПРОЕКТА

**Service Oper Uchet** - это enterprise-система синхронизации корпоративных данных для автоматизации процессов управления продажами с интеграцией Excel и PostgreSQL.

### 🚀 Ключевые возможности

- 🔄 **Умная синхронизация**: полная и инкрементальная синхронизация с настраиваемыми периодами
- 🛡️ **Продвинутая валидация**: контроль структуры Excel, финансовая сверка, обнаружение сдвигов данных
- 📊 **Веб-интерфейс**: современный React UI для просмотра, поиска и управления данными
- 📈 **Мониторинг**: dashboard с аналитикой, системой предупреждений и отчетами
- 🧪 **Высокое покрытие тестами**: 367 тестов (100% success rate)
- 🔐 **Enterprise-безопасность**: JWT аутентификация, ролевая модель, аудит всех операций
- ⚡ **Высокая производительность**: поддержка файлов до 50MB, обработка 1000+ сделок

---

## 📖 СТРУКТУРА ДОКУМЕНТАЦИИ

### 🎯 Основные документы

| Документ | Описание | Аудитория |
|----------|----------|-----------|
| **[PROJECT_DOCUMENTATION_MASTER.md](PROJECT_DOCUMENTATION_MASTER.md)** | Полная документация проекта | Все пользователи |
| **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** | Быстрый старт для разработчиков | Новые разработчики |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | REST API документация | Разработчики, интеграторы |
| **[USER_GUIDE.md](USER_GUIDE.md)** | Руководство пользователя | Конечные пользователи |
| **[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)** | Руководство разработчика | Разработчики, DevOps |
| **[DATABASE_DESIGN.md](DATABASE_DESIGN.md)** | Архитектура базы данных | Архитекторы, DBA |
| **[SYNC_FLOW.md](../project_progress/SYNC_FLOW.md)** | Полный поток синхронизации (Excel → Events → Read Models) | Разработчики |

### 📊 Техническая документация

| Документ | Описание | Статус |
|----------|----------|--------|
| **[TESTING_PLAN_AND_DESCRIPTION.md](TESTING_PLAN_AND_DESCRIPTION.md)** | План и описание тестирования | ✅ Актуально |
| **[REAL_DATA_TESTING_SCENARIOS.md](REAL_DATA_TESTING_SCENARIOS.md)** | Сценарии тестирования на реальных данных | ✅ Актуально |
| **[CODE_ANALYSIS_REPORT.md](CODE_ANALYSIS_REPORT.md)** | Анализ кода и архитектуры | ✅ Актуально |

### 📁 Архивные документы

| Документ | Описание | Статус |
|----------|----------|--------|
| **[Archive/HANDOVER_STATUS.md](Archive/HANDOVER_STATUS.md)** | Статус передачи проекта | 📋 Архив |
| **[Archive/PROJECT_HEALTH_CHECK.md](Archive/PROJECT_HEALTH_CHECK.md)** | Проверка состояния проекта | 📋 Архив |
| **[Archive/TESTING_COMMANDS.md](Archive/TESTING_COMMANDS.md)** | Команды тестирования | 📋 Архив |
| **[Archive/TESTING_EVOLUTION_PLAN.md](Archive/TESTING_EVOLUTION_PLAN.md)** | План эволюции тестирования | 📋 Архив |

### 📋 Отчеты и статусы

| Документ | Описание | Дата |
|----------|----------|------|
| **[PROJECT_TESTING_REPORT.md](PROJECT_TESTING_REPORT.md)** | Отчет о тестировании проекта | 27.01.2025 |
| **[TESTING_SYSTEM_CREATED.md](TESTING_SYSTEM_CREATED.md)** | Создание системы тестирования | 27.01.2025 |
| **[todo.txt](todo.txt)** | Список задач и TODO | Актуально |

---

## 🚀 БЫСТРЫЙ СТАРТ

### Для новых разработчиков

1. **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - начните здесь для понимания архитектуры
2. **[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)** - настройка окружения разработки
3. **[PROJECT_DOCUMENTATION_MASTER.md](PROJECT_DOCUMENTATION_MASTER.md)** - полная документация

### Для конечных пользователей

1. **[USER_GUIDE.md](USER_GUIDE.md)** - руководство по использованию системы
2. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - если нужен API доступ

### Для интеграторов

1. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - полная документация API
2. **[DATABASE_DESIGN.md](DATABASE_DESIGN.md)** - структура базы данных

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА

### ✅ Завершенные компоненты (100%)

- **Sprint 0**: Фундамент (DDD архитектура, доменные модели)
- **Sprint 1**: Core Business Logic (Event Sourcing, CQRS, все сервисы)
- **Sprint 2.1**: FastAPI + Auth (REST API, JWT, RBAC)
- **Sprint 2.2**: React Dashboard (современный UI, TypeScript)

### 🔄 Активный Sprint 2.3: Real Integration

- ✅ **Database Setup** - SQLite + PostgreSQL поддержка
- 🔄 **Mock Services Replacement** - замена на реальные сервисы (в работе)

### 📈 Статистика

| Метрика | Значение | Статус |
|---------|----------|---------|
| **Общие тесты** | 367/367 | ✅ 100% success |
| **Unit тесты** | 344 | ✅ Стабильны |
| **Integration тесты** | 17 | ✅ Стабильны |
| **E2E тесты** | 6 | ✅ Стабильны |
| **Время выполнения тестов** | ~3.5 мин | ✅ Оптимально |
| **Code Quality** | Ruff + TypeScript | ✅ Excellent |
| **Архитектура** | DDD + Event Sourcing | ✅ Modern |

---

## 🏗️ АРХИТЕКТУРА

### Архитектурные слои (DDD)

```
src/
├── domain/              # Бизнес-логика предметной области
│   ├── models/          # Сущности (Deal, DealItem, SyncSession)
│   ├── value_objects/   # Объекты-значения (Money, Money5, SignedMoney, SignedMoney5, Period, Status)
│   ├── exceptions/      # Доменные исключения
│   └── interfaces/      # Интерфейсы репозиториев
├── application/         # Сценарии использования
│   ├── excel_parser/    # Парсинг Excel файлов
│   ├── change_detector/ # Обнаружение изменений
│   ├── sync_orchestrator/ # Управление синхронизацией
│   └── data_validator/  # Валидация данных
├── infrastructure/      # Внешние сервисы
│   ├── database/        # БД и репозитории
│   ├── file_system/     # Работа с файлами
│   ├── scheduler/       # Планировщик задач
│   └── workers/         # Фоновые воркеры
└── presentation/        # Пользовательские интерфейсы
    ├── api/            # REST API (FastAPI)
    └── web/            # Web UI (React + TypeScript)
```

### Технический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Backend** | FastAPI | 0.104+ |
| **Database** | PostgreSQL/SQLite | 16+/3.35+ |
| **Frontend** | React + TypeScript | 18+ |
| **Testing** | pytest + Vitest | 7.4+ |
| **Linting** | Ruff + ESLint | 0.1+ |

---

## 🔄 КРАТКО О СИНХРОНИЗАЦИИ

- Вход: Excel парсится `ExcelParserService.parse_file` → `ParseResult (deals + items)`.
- События: оркестратор формирует `DealCreated/DealItemAdded` (full) или `DealCreated/DealUpdated/DealDeleted` (incremental) и пишет в `event_store`.
- Обработка: `ReadModelBuilder.process_latest_events(limit)` применяет события по `(aggregate_id, sequence_number)`, обновляя `read_deals`, `read_positions`, `read_stats`.
- Детали логики (версионирование позиций, soft‑delete, лимиты, форматы): `project_progress/SYNC_FLOW.md`.

---

## 🧪 ТЕСТИРОВАНИЕ

### Тестовая пирамида

- **Unit тесты (70%)** - 344 теста, быстрые тесты с моками (~15 сек)
- **Integration тесты (20%)** - 17 тестов, тесты с реальной БД (~1 мин)
- **E2E тесты (10%)** - 6 тестов, полный пайплайн через HTTP API (~2 мин)

### Запуск тестов

```bash
# Все тесты
python -m pytest

# Только unit тесты (быстро)
python -m pytest -m "unit"

# Интеграционные тесты
python -m pytest -m "integration"

# E2E тесты
python -m pytest -m "e2e"
```

---

## 🚧 ИЗВЕСТНЫЕ ПРОБЛЕМЫ И TODO

### Критические задачи

1. **Поле invoice_date в БД** - varchar вместо DATE
   - Изменить структуру данных
   - Обновить логику загрузки
   - Привести в соответствие API и frontend

2. **Несоответствие seller/saller** - привести к единому виду

3. **Удаление currency_amount полей** - упростить модель данных

4. **Вкладка синхронизации** - исправить функциональность

### Улучшения

- Полное тестирование на реальных данных
- Автоматизация развертывания (Docker)
- CI/CD pipeline
- Расширенный мониторинг
- Документация API (OpenAPI)

---

## 📞 ПОДДЕРЖКА

### Получение помощи

1. **Проверьте документацию** - большинство вопросов уже освещены
2. **Создайте Issue** в репозитории с описанием проблемы
3. **Обратитесь к администратору** системы

### Контакты

- **Техническая поддержка**: support@company.com
- **Администратор системы**: admin@company.com
- **GitHub Issues**: https://github.com/Vitalylqw/service_oper_uchet/issues

---

## 📄 ЛИЦЕНЗИЯ

MIT License - см. файл [LICENSE](../LICENSE)

---

**Разработано для**: Корпоративные системы управления продажами  
**Платформа**: Cross-platform (Windows, Linux, macOS)  
**Интеграция**: PostgreSQL, Excel  
**Архитектура**: DDD, Event Sourcing, CQRS  
**Статус**: Production Ready ✅

---

*Последнее обновление: 27 января 2025* 