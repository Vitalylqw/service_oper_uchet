# Комментарии к «Окончательному плану проекта»

## Ключевые упрощения и их мотивация

1. **Моно-репозиторий + Poetry workspace**  
   Меньше overhead на CI/CD, проще управление зависимостями. Выделять репозитории будем, когда появится второй потребитель.

2. **Отсутствие отдельного file-monitor сервиса**  
   Задача забора файла раз в сутки тривиальна; реализуется внутри `sync-service` (APScheduler).

3. **Единый контейнер `sync-service`**  
   Orchestrator, scheduler и persister имеют общие зависимости; преждевременное разделение усложнит DevOps.

4. **Redis вместо RabbitMQ/Kafka**  
   Начальная нагрузка < 10 k событий/день. Redis проще в поддержке; Kafka в backlog.

5. **Upcaster-framework рядом с миграциями**  
   Это implementation-detail БД; отдельный репозиторий избыточен.

6. **`read-model-builder` как один worker**  
   Текущие объёмы не требуют горизонтального масштабирования. При росте — клонируем deployment.

7. **FastAPI в `sync-service`**  
   Даёт `/healthz`, метрики и REST-точки управления (триггер ручной синхронизации).

---

## Основные риски и способы их снизить

| Риск | Смягчение |
|------|-----------|
| Нагрузка > 100 k событий/день | Выделить `change-detector` в сервис; Kafka; autoscaling workers |
| Ошибка в Excel-parser рушит пайплайн | Integration-тесты; graceful-fail → email-alert |
| Сложность upcaster-ов | `schema_version` в payload, миграции как функции |

---

## Выбор технологий

* **Pydantic v2** – высокая скорость, минимум зависимостей.
* **SQLAlchemy 2 Core** – прозрачная работа sync/async, понятные миграции.
* **Celery | RQ + Redis** – быстро разворачивается, знакома большинству Python-разработчиков.
* **React 18 + Vite** – быстрый dev-server, современный DX.

---

## Грубая оценка трудозатрат (person-days)

| Этап | PD |
|------|----|
| Sprint 0 | 25 |
| Sprint 1 | 40 |
| Sprint 2 | 45 |
| Release Candidate | 15 |
| GA | 10 |
| **Итого** | **135** |

---

## Следующие шаги после утверждения

1. Создать репозиторную структуру (Poetry workspace, шаблон CI).  
2. Подготовить ADR 0001 «Event Sourcing vs. plain history tables».  
3. Запустить Sprint 0 – core-domain + excel-parser. 