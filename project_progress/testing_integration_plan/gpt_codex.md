# План тестового проекта Excel → PostgreSQL

**Варианты реализации**

- **A. Встроенный под-проект в текущем репо** (`testing/excel_regression_lab`). Плюсы: совместное использование docker-compose/migrations, единый CI, нет расхождений версий. Минусы: тесная связь с основным кодом, дольше прогоны.
- **B. Выделенный репозиторий** с git submodule на основной сервис. Плюсы: изоляция, можно масштабировать инфраструктуру. Минусы: усложненный диплой, требуется отдельный процесс синхронизации схем и артефактов.
**Рекомендация:** стартовать с варианта A для минимальной инерции, держать B как эволюционный шаг, когда тестовая ферма станет узким местом.

## Шаг 1. Аналитика и документация

- Изучить текущую схему БД и правила синхронизации, зафиксировать выводы в [`project_progress/PROJECT_OVERVIEW.md`](project_progress/PROJECT_OVERVIEW.md) и новом документе `project_progress/TEST_PROJECT_BRIEF.md` (цель тест-проекта, сервисы, ожидания по покрытию).
- Расписать процесс загрузки Excel, текущие точки детектирования изменений и потенциальные риски в `project_progress/DEVELOPMENT_JOURNAL.md` и `project_progress/status.md`.
- Разработать RAG-конспект структуры файлов Excel (шаблон листа, названия колонок) в `project_progress/EXCEL_FORMAT_REFERENCE.md` для быстрых справок.

## Шаг 2. Скелет тестового проекта

- Создать дерево `testing/excel_regression_lab/` с `pyproject.toml` (dependencies: `pytest`, `pytest-xdist`, `pandas`, `openpyxl`, `sqlalchemy`, `psycopg[binary]`, `faker`, `datamodel-code-generator` для фикстур).
- Настроить `pytest.ini`, `ruff.toml`, `mypy.ini`, `conftest.py` (общие фикстуры: временный каталог Excel, подключение к БД, REST/CLI клиент сервиса).
- Добавить `docker-compose.regression.yml`, наследующийся от `docker-compose.db.yml`, чтобы поднимать PostgreSQL + контейнер приложения (FastAPI/worker) в тестовом окружении.
- Подготовить `scripts/test/run_excel_regression.py` + `.bat` для Windows, чтобы запуск был одинаковым локально и в CI.

## Шаг 3. Каталог Excel-сценариев

- Создать `testing/excel_regression_lab/data/base/BaseWorkbook.xlsx` — "эталон".
- Добавить генератор `testing/excel_regression_lab/data/generator.py`, который на основе YAML-описаний сценариев собирает Excel-файлы (использовать `openpyxl`, `faker`), хранить YAML в `testing/excel_regression_lab/data/scenarios/*.yml`.
- Для каждого сценария подготовить инструкцию в `testing/excel_regression_lab/docs/scenario_catalog.md` с точными действиями в файле:
- **S0_Baseline**: загрузить "чистый" файл; ожидаем заполнение всех таблиц без изменений.
- **S1_NewDeals**: скопировать лист "Март 2025", в блоке клиента `ООО Вектор` добавить новый ряд сделки (заполнить столбцы "Клиент", "Счет", "Отгрузка", суммы; добавить 2 строки позиций). Проверка: появление новой записи в `read_deals`, новые позиции в `read_positions`, `sync_sessions.total_deals` увеличился.
- **S2_UpdateFields**: в листе "Апрель 2025" найти сделку `ООО Ромашка / счет 5938`, изменить `total_margin`, `is_paid`, `seller`, а также маржу у одной позиции. Проверка: событие `DealUpdated`, обновленные поля и hash_key пересчитан.
- **S3_DeleteDeal**: удалить блок клиента `ООО Север` (строки сделки и позиций). Проверка: запись помечена удаленной (через событие `DealDeleted` или отсутствует в read-модели), синхронизация корректно обрабатывает "пропажу".
- **S4_DeletePosition**: в сделке `ООО Ромашка` убрать одну позицию, пересчитать итоги. Проверка: позиция удалена, totals пересчитаны, `items_count` уменьшился.
- **S5_MoveBetweenSheets**: перенести сделку `ООО Альфа` из листа "Март 2025" в новый лист "Апрель 2025" (с сохранением строк), убедиться что новые значения `period_*` пересчитаны.
- **S6_NewSheetAdded**: создать лист "Июнь 2025" с тем же хедером, вставить 1-2 сделки. Проверка: динамическое обнаружение новых листов, корректная привязка периода.
- **S7_ColumnReorder**: поменять порядок колонок в одном листе (например, переместить `total_margin` перед `total_revenue`). Проверка: парсер устойчив к порядку, данные совпали.
- **S8_NumberFormats**: применить Excel-формулы/формат с запятыми, добавить округления. Проверка: конвертация чисел, отсутствие дрейфа.
- **S9_DuplicateDetection**: продублировать сделку (те же invoice + client). Проверка: сервис обнаруживает дубликат и выбрасывает предупреждение.
- **S10_MetadataNoise**: добавить скрытый лист, примечания, строки с мусором до заголовка. Проверка: `_find_header_row` справляется, синхронизация устойчивa.
- Для сценариев S1-S10 описать ожидания по БД (какие таблицы, какие поля должны измениться) и правила ручной правки: какие конкретно столбцы менять, какие значения рекомендуется ставить (например, `total_margin` увеличить на 5000, `is_paid` → "Да", `pickup_date` → "19.06.2025").

## Шаг 4. Контур запуска импорта

- Реализовать клиент `testing/excel_regression_lab/harness/import_runner.py`, который:

1. Загружает Excel в сервис (REST endpoint `/api/v1/sync/upload` либо CLI `python excel_parser.py path`).
2. Поллит статус `sync_sessions` до завершения.
3. Возвращает итоговые статистики + снапшоты `read_deals`, `read_positions`.

- Настроить фикстуру `app_context` в `tests/conftest.py` (инициализация docker-compose, прогон миграций командой из [`run_migrations.sh`](run_migrations.sh)), добавить логирование всех запросов/SQL.

## Шаг 5. Интеграционные тесты

- Разработать DSL `ScenarioDefinition` (Pydantic-модель) + `ScenarioExecutor`, чтобы каждый `.yml` сценарий конвертировался в pytest test case.
- Структура тестов: `tests/integration/test_scenarios.py` (параметризованный `pytest.mark.parametrize("scenario", SCENARIOS)`), `tests/integration/test_resilience.py` (нагрузочные/повторные запуски), `tests/integration/test_schema_drift.py`.
- Каждому сценарию сопоставить assert-ы:
- снимок таблиц до/после (`SELECT ... FROM read_deals ORDER BY ...`),
- сравнение JSON сериализаций (использовать helper `assert_deal_snapshot(expected.json)`),
- проверка событий (`event_store`).
- Добавить smoke-тест для добавления нового листа (S6) и e2e-тест на цепочку изменений (S1→S2→S4 в одном прогоне).

## Шаг 6. Отчетность и CI

- В `testing/excel_regression_lab/README.md` описать процесс запуска, структуру сценариев, правила правки Excel.
- Настроить GitHub Actions job `excel-regression.yml`: шаги `docker compose up`, `ruff`, `pytest -m regression --maxfail=1`, публикация артефактов (логи, итоговые Excel).
- Добавить генерацию Allure/pytest-html отчета, хранить в `testing/excel_regression_lab/reports/`.
- Зафиксировать в `project_progress/STATUS.md` текущий прогресс по сценариям и TODO (что осталось покрыть).