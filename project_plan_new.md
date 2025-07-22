# ОКОНЧАТЕЛЬНЫЙ ПЛАН ПРОЕКТА

## 0. high-level-docs (`docs/`)
Назначение: архитектурные решения (ADR), диаграммы, схемы БД, стандарты логирования, Contributing.

## 1. core-domain (`libs/core_domain`)
- Pydantic v2 модели: `Deal`, `DealItem`, `SyncSession`, `DomainError`.
- Value Objects: `Money`, `Period`, `HashKey`.
- Никаких внешних зависимостей, кроме `pydantic-core`.
- 100 % `mypy` + `ruff`.
- Публикация через Poetry workspace (`core-domain-x.y.z`).

## 2. excel-parser (`services/excel_parser`)
- Pandas/OpenPyXL + core-domain.
- CLI: `excel-parse <file> --json`.
- Unit-coverage ≥ 95 %.
- Только парсинг — без бизнес-логики сравнения данных.
- Structured-logs + `ParseStats`.

## 3. change-detector (`libs/change_detector`)
- Хэширование записей, классификация INSERT/UPDATE/DELETE.
- Стратегии: full-sync, incremental-sync (N месяцев).
- Работает на структурах core-domain.
- 90 %+ покрытие.

## 4. event-store (`infra/db/migrations`)
- Alembic 2 + SQLAlchemy 2, таблица `event_store` (JSONB).
- Скрипты партиционирования и GIN-индекса.
- Upcaster-framework в том же пакете.

## 5. sync-service (`services/sync_service`)
Единый контейнер FastAPI / CLI:
1. Orchestrator — создаёт `SyncSession`, вызывает file-fetcher → excel-parser → change-detector → persister.  
2. Persister — batch-insert событий + update read-model в транзакции.  
3. Scheduler — APScheduler.  
4. Retry / alert logic — Loguru + SMTP.

## 6. read-model-builder (`workers/read_model_builder`)
- Celery | RQ worker, LISTEN/NOTIFY от `event_store`.
- Обновляет схемы `read_deals`, `read_positions`, `read_stats`.
- Хранит watermark в `worker_state`.

## 7. api-gateway (`services/api_gateway`)
- FastAPI (async) → read-schema.
- RBAC: fastapi-users + JWT (15 min / 7 days).
- Pydantic v2 только для сериализации.
- OpenAPI + Swagger-UI.

## 8. web-ui (`apps/web_ui`)
- React 18 + Vite + TypeScript, ECharts.
- Artefact `dist/` отдаёт Nginx.
- Только READ-операции (CQRS).

## 9. monitoring-stack (`ops/monitoring`)
- docker-compose overlay: Prometheus, Grafana, Loki, Alertmanager.
- Готовый dashboard «Sync Performance».

## 10. infra-as-code (`ops/iac`)
- Terraform + Ansible:
  - ВМ, PostgreSQL 16 (Patroni), reverse-proxy, SMTP relay.
- GitHub Actions: lint → tests → docker-build → push ghcr.io → deploy(Ansible).

## 11. integration-tests (`tests/integration`)
- Pytest + docker-compose-up stack.
- Проверяет: полный цикл sync → read-API, rollback on error, perf < 5 min @1k deals.

---

## Минимальная Roadmap (MVP → GA)

| Спринт | Задачи | Длительность |
|--------|--------|--------------|
| Sprint 0 | core-domain, excel-parser (tests); change-detector; event_store миграции; Makefile | 1 неделя |
| Sprint 1 | sync-service orchestrator + persister; интеграционный тест; read-model-builder (basic); api-gateway /deals | 2 недели |
| Sprint 2 | Scheduler + retry; интеграция 1С-bridge (mock); Web-UI (Dashboard + Deal list); Monitoring | 2 недели |
| RC | Perf-tests @ 1k deals / 50 MB; security hardening; backup scripts | 1 неделя |
| GA | Alerting, SLA dashboards, документация | 1 неделя |

---

## Расширения в Backlog
- Kafka вместо Redis, если > 50k событий/день.
- Выделение change-detector в отдельный сервис при росте нагрузки.
- gRPC-канал вместо REST для внутренних вызовов.
- Helm charts для Kubernetes-деплоя. 