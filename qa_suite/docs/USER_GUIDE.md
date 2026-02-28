# Руководство пользователя QA Suite

## 1. Быстрый старт

### 1.1 Запуск всех тестов

```bash
cd qa_suite/scripts
run_all_tests.bat
```

### 1.2 Запуск отдельного сценария

```bash
cd qa_suite/scripts
run_single_scenario.bat TEST_INS_01
```

### 1.3 Очистка тестовой БД

```bash
cd qa_suite/scripts
clear_test_db.bat
```

## 2. Конфигурация

### 2.1 Настройки БД

Настройки читаются из `config.env` в корне проекта или переменных окружения:

```env
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

### 2.2 Настройки QA Suite

Дополнительные настройки через переменные с префиксом `QA_SUITE_`:

```env
QA_SUITE_CONTINUE_ON_ERROR=true
QA_SUITE_VERBOSE_LOGGING=true
QA_SUITE_CLEANUP_TEMP_FILES=true
```

## 3. Создание тестовых сценариев

### 3.1 Структура YAML сценария

Создайте файл в `tests/scenarios/`:

```yaml
scenarios:
  - id: TEST_XXX_01
    name: "Название сценария"
    description: "Описание теста"
    category: INSERT  # INSERT, UPDATE, DELETE, MIXED, EDGE
    enabled: true
    
    setup:
      base_state: "base_state.xlsx"
      clear_db_before: false
      sync_base_first: true
    
    actions:
      - type: add_sheet
        sheet_name: "Июнь 2025"
        deals:
          - client_name: "ООО Тест"
            invoice_info: "1001 от 01.06.2025"
            seller: "Продавец"
            items:
              - product_name: "Товар"
                quantity: 10
                purchase_price: 100.00
                sale_price: 150.00
    
    expected:
      changes:
        insertions: 2
        updates: 0
        deletions: 0
      db_state:
        deals_count: "+1"
      sync_success: true
```

### 3.2 Типы действий (actions)

| Тип | Описание | Параметры |
|-----|----------|-----------|
| add_sheet | Добавить лист | sheet_name, deals |
| remove_sheet | Удалить лист | sheet_name |
| add_deal | Добавить сделку | sheet_name, deals |
| remove_deal | Удалить сделку | sheet_name, deal_key |
| update_deal_field | Изменить поле сделки | sheet_name, deal_key, field_name, field_value |
| add_position | Добавить позицию | sheet_name, deal_key, items |
| remove_position | Удалить позицию | sheet_name, deal_key, position_number |
| update_position_field | Изменить поле позиции | sheet_name, deal_key, position_number, field_name, field_value |

### 3.3 Ожидаемые результаты

#### Изменения (changes)
```yaml
expected:
  changes:
    insertions: 5  # Новые записи
    updates: 2     # Обновленные записи
    deletions: 1   # Удаленные записи
```

#### Состояние БД (db_state)
```yaml
expected:
  db_state:
    deals_count: "+1"      # Относительное изменение
    positions_count: "10"  # Абсолютное значение
    deals_in_period:
      "Май 2025": 3
    deal_exists:
      - "5938|16.05.2025|крепеж-инструмент ооо|май 2025"
    deal_not_exists:
      - "9999|01.01.2025|тест|январь 2025"
```

#### События (events)
```yaml
expected:
  events:
    - type: DealCreated
      count: 1
    - type: DealItemAdded
      count: 3
```

## 4. Отчеты

### 4.1 Расположение отчетов

Отчеты сохраняются в `qa_suite/reports/`:

- `test_run_YYYYMMDD_HHMMSS.json` - JSON отчет
- `test_run_YYYYMMDD_HHMMSS.html` - HTML отчет
- `latest_report.json` - последний JSON
- `latest_report.html` - последний HTML

### 4.2 Структура JSON отчета

```json
{
  "run_id": "uuid",
  "timestamp": "2026-01-12T10:00:00",
  "total_scenarios": 20,
  "passed": 18,
  "failed": 2,
  "scenarios": [...],
  "aggregates_before": {...},
  "aggregates_after": {...},
  "aggregate_diff": {...}
}
```

### 4.3 Просмотр HTML отчета

Откройте `reports/latest_report.html` в браузере для визуального просмотра результатов.

## 5. Категории сценариев

| Категория | Описание |
|-----------|----------|
| INSERT | Добавление новых данных |
| UPDATE | Изменение существующих данных |
| DELETE | Удаление данных |
| MIXED | Комбинированные операции |
| EDGE | Граничные случаи (идемпотентность, пустые файлы, дубликаты) |

## 6. Troubleshooting

### 6.1 Ошибка подключения к БД

Проверьте:
- PostgreSQL запущен
- Настройки в config.env корректны
- Сетевой доступ к БД

### 6.2 Сценарий не найден

Убедитесь что:
- Файл сценария в `tests/scenarios/`
- Формат файла `.yaml` или `.yml`
- `enabled: true` в сценарии

### 6.3 Некорректные результаты

Проверьте:
- Базовый файл `base_state.xlsx` существует
- Сценарий корректно описывает ожидаемые изменения
- БД очищена перед тестами (если требуется)

## 7. Программный доступ

### 7.1 Запуск из Python

```python
import asyncio
from pathlib import Path
from qa_suite.config import get_settings
from qa_suite.core.test_runner import TestRunner
from qa_suite.core.reporters import ReportManager

async def run_tests():
    settings = get_settings()
    
    runner = TestRunner(
        scenarios_dir=settings.scenarios_dir,
        fixtures_dir=settings.fixtures_dir,
        temp_dir=settings.temp_dir,
        reports_dir=settings.reports_dir,
        database_url=settings.database_url,
    )
    
    report = await runner.run_all_scenarios()
    
    reporter = ReportManager(settings.reports_dir)
    reporter.generate_all_reports(report)
    
    await runner.cleanup()

asyncio.run(run_tests())
```

### 7.2 Создание Excel файла программно

```python
from qa_suite.core.excel_builder import ExcelBuilder
from qa_suite.core.models import DealData, ItemData

builder = ExcelBuilder.create_new()

deal = DealData(
    client_name="Тест",
    invoice_info="100 от 01.01.2025",
    seller="Продавец",
    items=[
        ItemData(product_name="Товар 1", quantity=10, purchase_price=100, sale_price=150)
    ]
)

builder.add_sheet("Январь 2025", [deal])
builder.save(Path("test.xlsx"))
```
