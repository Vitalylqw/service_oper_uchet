# Service Oper Uchet – Documentation Hub

> Этот файл – точка входа для всех разработчиков. Здесь собраны правила репозитория, структура каталогов и основные команды.

## 1. Цель проекта
Система синхронизации данных из Excel в PostgreSQL с Event Sourcing + CQRS. Python 3.11, FastAPI, SQLAlchemy 2, React 18.

## 2. Структура репозитория
| Путь | Содержание |
|------|------------|
| `src/domain` | DDD-модели, Value Objects, Exceptions |
| `src/application` | Сервисы use-case уровня (`excel_parser`, `change_detector`, …) |
| `src/infrastructure` | БД, файловая система, планировщик, воркеры |
| `src/presentation` | FastAPI, CLI, React front |
| `tests/` | Unit / Integration / E2E |
| `scripts/` | Локальные утилиты и примеры запросов |
| `docs/` | Активная документация (этот каталог) |
| `docs/Archive/` | Исторические материалы и черновики |

## 3. Git-workflow
Simplified GitFlow.

* `main` – продакшен. Мерж только через PR + CI + ревью.
* `develop` – интеграционная ветка. Все спринты мержатся сюда.
* `feature/<task>` – новая функциональность.
* `fix/<bug>` – исправление бага.
* `chore/<topic>` / `docs/<topic>` – служебные изменения.
* `release/<version>` – подготовка релиза.
* `hotfix/<issue>` – экстренный фикс продакшена.

### 3.1 Правила Pull Request
1. CI (pytest + ruff + black --check) должен быть зелёным.
2. Минимум 1 ревьюер.
3. Squash-merge, название коммита = PR-title.
4. Запрещён push в `main` / `develop`.

### 3.2 Conventional Commits (EN)
```
<type>(scope): message

[optional body]
```
Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`.

### 3.3 Branch protection
Добавить в GitHub > Settings > Branches:
* required status checks: `ci/tests`, `ci/ruff`.
* require pull request reviews.

## 4. CI
GitHub Actions `python.yml`:
1. `poetry install --with dev`  
2. `ruff check .`  
3. `black --check .`  
4. `pytest -q`  
5. Upload coverage to Codecov.

## 5. Локальная разработка
```bash
# установка зависимостей
poetry install --with dev

# запуск API
poetry run uvicorn src.presentation.api.main:app --reload

# linters & tests
poetry run ruff check .
poetry run black .
poetry run pytest -q
```

## 6. Контакты
Все вопросы – в Slack-канал `#service-oper-uchet`.

---
_Last update: 24 июля 2025_ 