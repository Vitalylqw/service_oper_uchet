# QA Suite - Integration Testing Framework

Изолированный стенд для интеграционного тестирования логики синхронизации Excel-БД.

## Быстрый старт

```bash
# Запуск всех тестов
cd qa_suite/scripts
run_all_tests.bat

# Запуск конкретного сценария
run_single_scenario.bat TEST_INS_01

# Запуск по категории
run_by_category.bat INSERT

# Очистка БД
clear_test_db.bat
```

## Структура

```
qa_suite/
  config/           # Настройки
  core/             # Ядро системы
    excel_builder.py    # Генерация Excel
    db_manager.py       # Управление БД
    scenario_loader.py  # Загрузка сценариев
    test_runner.py      # Исполнитель тестов
    validators.py       # Валидация результатов
    reporters.py        # Генерация отчетов
    models.py           # Модели данных
  docs/             # Документация
  tests/
    scenarios/      # YAML сценарии
    fixtures/       # Базовые Excel файлы
  reports/          # Выходные отчеты
  scripts/          # Скрипты запуска
```

## Документация

- [Техническое задание](docs/TECHNICAL_SPEC.md)
- [Структура Excel файла](docs/EXCEL_DATA_STRUCTURE.md)
- [Логика детектирования](docs/CHANGE_DETECTION_LOGIC.md)
- [Руководство пользователя](docs/USER_GUIDE.md)

## Категории тестов

| Категория | Сценарии | Описание |
|-----------|----------|----------|
| INSERT | TEST_INS_01-03 | Добавление данных |
| UPDATE | TEST_UPD_01-05 | Изменение данных |
| DELETE | TEST_DEL_01-04 | Удаление данных |
| MIXED | TEST_MIX_01-03 | Комбинированные операции |
| EDGE | TEST_EDGE_01-07 | Граничные случаи |

## Требования

- Python 3.11+
- PostgreSQL 13+
- Зависимости проекта (requirements.txt)

## Конфигурация

Настройки читаются из `config.env` в корне проекта:

```env
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

## Отчеты

После прогона отчеты сохраняются в `reports/`:

- `test_run_YYYYMMDD_HHMMSS.json` - JSON отчет
- `test_run_YYYYMMDD_HHMMSS.html` - HTML отчет
- `latest_report.html` - последний отчет

Открыть последний отчет:
```bash
scripts/view_latest_report.bat
```
