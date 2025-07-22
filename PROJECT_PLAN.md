# Концептуальный план реализации системы синхронизации Excel → PostgreSQL

Ниже приведён план, разбитый на отдельные проекты/модули. Такая декомпозиция позволяет:

* изолировать области ответственности;
* упростить CI/CD и управление зависимостями;
* масштабировать каждый компонент независимо;
* минимизировать влияние изменений одного сервиса на остальные.

---
## 1. domain-models (общая библиотека)
Назначение: единое описание предметной области (сделки, позиции, сессии синхронизации и т.д.).

Содержит:
* Pydantic-модели с типами (PEP 484) и валидацией;
* value-objects (денежные значения, период, статус и т.д.);
* доменные исключения.

Формат: чистая Python-библиотека, без сторонних зависимостей, публикуемая во внутренний PyPI.

---
## 2. excel-parser
Назначение: чтение и валидация Excel-файлов.

Содержит:
* слой infrastructure для доступа к файлу;
* слой application, реализующий «ParseExcelCommand»;
* unit-тесты на типовые и ошибочные файлы (> 95 % покрытия для критичных путей);
* CLI-утилиту `excel-parser validate <file>` для локальной проверки.

Использует: pandas, openpyxl, loguru.

---
## 3. change-detector
Назначение: сравнение новой выборки с предыдущей версией и классификация INSERT/UPDATE/DELETE.

Содержит:
* алгоритмы хэширования записей;
* стратегию полной и инкрементальной синхронизации;
* адаптеры к PostgreSQL (чтение предыдущего состояния);
* unit-тесты на все сценарии.

---
## 4. event-store (PostgreSQL schema + миграции)
Назначение: хранение необработанных событий в формате Event Sourcing.

Содержит:
* SQL-миграции (Alembic) для таблицы `event_store`;
* upcaster-framework (Python) для миграции старых событий;
* тесты производительности индексов и партиций.

---
## 5. sync-service
Назначение: оркестрация ежедневной синхронизации «файл → БД».

Компоненты:
1. orchestrator (application layer)
   * создаёт сессию;
   * получает файл (file-monitor client);
   * вызывает excel-parser → change-detector → persister.
2. persister (infrastructure layer)
   * записывает события в `event_store`;
   * обновляет read-model внутри транзакции.
3. scheduler
   * APScheduler (основной);
   * резервный вызов Windows Task Scheduler.
4. monitoring / retry logic.

---
## 6. read-model-builder
Назначение: формирование проекций (CQRS read-side).

Реализация:
* Celery worker получает события из event-store (polling) или через pg_notify;
* обновляет схемы `read_deals`, `read_positions`, `read_stats`;
* хранит контрольные точки (last_event_id).

---
## 7. api-gateway (FastAPI)
Назначение: REST API для внешних клиентов и внутренних сервисов.

Функции:
* CRUD-эндпоинты (только READ по CQRS);
* фильтрация и пагинация;
* эндпоинты истории изменений;
* интеграция с OAuth 2.1 (PKCE), RBAC (admin/analyst/viewer);
* OpenAPI + Swagger.

---
## 8. web-ui (React + TypeScript или Vue 3)
Назначение: пользовательский интерфейс (Dashboard, каталог сделок, аудит).

Особенности:
* отдельный SPA с компонентами для графиков (Chart.js / ECharts);
* использует api-gateway.

---
## 9. monitoring-stack
Назначение: сбор и визуализация метрик/логов.

Состав:
* Prometheus + Grafana (метрики);
* Loki (логи JSON из всех сервисов);
* Alertmanager (email-alerts);
* готовые dashboards: «Sync Performance», «Errors», «Database Load».

---
## 10. infra-as-code
Назначение: reproducible-инфраструктура.

Содержит:
* Terraform / Ansible playbooks: VM развёртывание, PostgreSQL cluster, SFTP-share, reverse-proxy;
* GitHub Actions workflows: lint → tests → build images → deploy;
* Docker Compose для локальной разработки.

---
## 11. integration-tests
Назначение: end-to-end тестирование полного цикла.

Функции:
* поднимает всё через Docker Compose;
* генерирует тестовый Excel, запускает sync-service, проверяет состояние БД и события;
* измеряет время выполнения (SLO).

---
### Взаимосвязи проектов
* domain-models — зависимость почти всех остальных.
* excel-parser и change-detector → sync-service.
* sync-service публикует события в event-store.
* read-model-builder формирует агрегированные таблицы.
* api-gateway обращается к read-model-schema.
* web-ui работает только с api-gateway.
* monitoring-stack агрегирует логи и метрики из всех сервисов.

---
### Репозиторная стратегия
1. **Mono-org** в GitHub:
   * каждый проект отдельный репозиторий → независимые версии, semantic-release;
   * общий template-репо (pytest, ruff, semantic-release config).
2. **Mono-repo** с каталогами `/services/*` и `/libs/*`; внутренняя версияция Poetry-workspace.

Выбор зависит от политики деплоя: если Kubernetes — лучше micro-repos; для упрощённого CI/CD можно mono-repo.

---
### Следующие шаги
1. Уточнить формат развертывания (Docker Compose vs K8s).
2. Зафиксировать репо-структуру и naming convention.
3. Создать baseline-репозитории с шаблонами CI (ruff + pytest).
4. Определить контракты между компонентами (OpenAPI, события).
5. Начать разработку с библиотек **domain-models** и **excel-parser** (критичные компоненты, требование 95 % покрытия). 