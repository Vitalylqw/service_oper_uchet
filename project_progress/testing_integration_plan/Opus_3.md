# План проекта интеграционного тестирования PEO

## 1. Структура тестового проекта

Создать отдельный проект `peo-integration-tests` с собственным git репозиторием:

```
peo-integration-tests/
|-- README.md
|-- pyproject.toml
|-- config.env                      # Конфигурация тестовой БД
|-- docker-compose.yml              # PostgreSQL для тестов
|-- src/
|   |-- generators/                 # Генераторы тестовых Excel файлов
|   |   |-- base_generator.py       # Базовый генератор Excel
|   |   |-- scenario_generator.py   # Генератор сценариев изменений
|   |   |-- data_factory.py         # Фабрика тестовых данных
|   |-- verifiers/                  # Верификаторы результатов
|   |   |-- db_verifier.py          # Проверка состояния БД
|   |   |-- change_verifier.py      # Проверка детектирования изменений
|   |   |-- event_verifier.py       # Проверка Event Store
|   |-- utils/                      # Утилиты
|   |   |-- db_helpers.py           # Работа с БД
|   |   |-- excel_helpers.py        # Работа с Excel
|-- tests/                          # pytest тесты
|   |-- conftest.py                 # Фикстуры
|   |-- test_deal_scenarios.py      # Тесты сценариев сделок
|   |-- test_item_scenarios.py      # Тесты сценариев позиций
|   |-- test_sheet_scenarios.py     # Тесты сценариев листов
|   |-- test_complex_scenarios.py   # Комплексные сценарии
|-- scripts/                        # Standalone скрипты
|   |-- run_scenario.py             # Запуск отдельного сценария
|   |-- run_all_tests.py            # Запуск всех тестов
|-- test_data/                      # Тестовые данные
|   |-- base/                       # Базовые Excel файлы
|   |-- scenarios/                  # Сгенерированные сценарии
|-- reports/                        # Отчеты о тестировании
```

---

## 2. Структура Excel файла (для справки при генерации)

### Название листа (Sheet)

Формат: `{Месяц} {Год}` или `{Month} {Year}`

- Примеры: `Январь 2025`, `February 2024`
- Period извлекается методом `Period.from_sheet_name()`

### Структура строк

```
Строка 1-5:  Заголовок (содержит слово "Клиент")
Строка N:    Master Record (сделка) - есть значение в колонке A
Строка N+1:  Detail Record (позиция) - колонка A пуста
Строка N+2:  Detail Record (позиция) - колонка A пуста
...
Строка M:    Master Record (следующая сделка)
```

### Колонки для Master Record (сделка)

| Индекс | Название | Поле модели | Обязательное |

|--------|----------|-------------|--------------|

| 0 | Клиент | client_name | Да |

| 1 | Счет | invoice_info | Да |

| 2 | Отгружен | is_shipped | Нет |

| 3 | УПД | upd_number | Нет |

| 4 | Оплачен | is_paid | Нет |

| 5 | Выручка | total_revenue | Нет |

| 6 | Маржа | total_margin | Нет |

| 7 | Продавец | seller | Да |

| 8 | Закупка | total_cost | Нет |

| 9 | Откат | kickback_amount | Нет |

### Колонки для Detail Record (позиция)

| Индекс | Название | Поле модели | Обязательное |

|--------|----------|-------------|--------------|

| 1 | Товар | product_name | Да |

| 2 | Кол-во | quantity | Нет |

| 3 | Цена закупки | purchase_price | Нет |

| 4 | Цена продажи | sale_price | Нет |

| 5 | Выручка | revenue | Нет |

| 6 | Маржа | margin | Нет |

| 8 | Себестоимость | cost | Нет |

| 9 | Поставщик | supplier_name | Нет |

| 10 | Дата забора | pickup_date | Нет |

---

## 3. Сценарии тестирования

### 3.1 Сценарии для сделок (Deals)

#### DEAL-INSERT: Новая сделка

**Как изменить файл:**

- Добавить новую строку Master Record с новым клиентом/счетом
- Добавить позиции под ней

**Проверки:**

- `ChangeDetectorService.detect_changes()` возвращает `INSERT` для Deal
- Event Store содержит событие `DealCreated`
- `read_deals` содержит новую запись
- Все поля соответствуют исходным данным

#### DEAL-UPDATE-STATUS: Изменение статусов

**Как изменить файл:**

- Изменить значение в колонке "Отгружен" (2) или "Оплачен" (4)
- Значения: "Да"/"Нет", "Отгружен", "Оплачен"

**Проверки:**

- `ChangeDetectorService` возвращает `UPDATE` с `field_changes` для `is_shipped`/`is_paid`
- Event Store содержит `DealUpdated` с корректными `field_changes`
- `read_deals.is_shipped_status` / `is_paid_status` обновлены

#### DEAL-UPDATE-FINANCIAL: Изменение финансовых полей

**Как изменить файл:**

- Изменить значения в колонках 5 (выручка), 6 (маржа), 8 (стоимость), 9 (откат)

**Проверки:**

- `field_changes` содержит `total_revenue`, `total_margin`, `total_cost`, `kickback_amount`
- Суммы в `read_deals` обновлены корректно
- Проверить точность Decimal (2 знака)

#### DEAL-UPDATE-UPD: Изменение УПД номера

**Как изменить файл:**

- Изменить значение в колонке 3 (УПД)

**Проверки:**

- `field_changes` содержит `upd_number`
- `read_deals.upd_number` обновлен

#### DEAL-DELETE: Удаление сделки

**Как изменить файл:**

- Удалить строку Master Record и все её позиции

**Проверки:**

- `ChangeDetectorService` возвращает `DELETE` для Deal
- Event Store содержит `DealDeleted`
- `read_deals.is_active = false` (soft delete)
- Все позиции этой сделки также `is_active = false`

### 3.2 Сценарии для позиций (DealItems)

#### ITEM-INSERT: Новая позиция

**Как изменить файл:**

- Добавить Detail Record под существующей сделкой
- position_number присваивается автоматически

**Проверки:**

- `ChangeDetectorService` возвращает `INSERT` для DealItem
- Event Store содержит `DealItemAdded`
- `read_positions` содержит новую запись
- `hash_key` рассчитан корректно
- Агрегаты сделки пересчитаны (`_recalculate_totals`)

#### ITEM-UPDATE-PRODUCT: Изменение товара

**Как изменить файл:**

- Изменить значение в колонке 1 (Товар)

**Проверки:**

- `field_changes` содержит `product_name`
- `hash_key` изменился (новая версия записи)
- Старая запись `is_active = false`, новая `is_active = true`

#### ITEM-UPDATE-QUANTITY: Изменение количества

**Как изменить файл:**

- Изменить значение в колонке 2 (Кол-во)

**Проверки:**

- `field_changes` содержит `quantity`
- Пересчитаны `revenue`, `cost`, `margin`
- Агрегаты сделки пересчитаны

#### ITEM-UPDATE-PRICE: Изменение цен

**Как изменить файл:**

- Изменить колонку 3 (цена закупки) или 4 (цена продажи)

**Проверки:**

- `field_changes` содержит `purchase_price`/`sale_price`
- Пересчитаны `cost`, `margin`
- Проверить точность Money5 (5 знаков для purchase_price)

#### ITEM-UPDATE-SUPPLIER: Изменение поставщика

**Как изменить файл:**

- Изменить значение в колонке 9 (Поставщик)

**Проверки:**

- `field_changes` содержит `supplier_name`
- `read_positions.supplier_name` обновлен

#### ITEM-DELETE: Удаление позиции

**Как изменить файл:**

- Удалить Detail Record

**Проверки:**

- `ChangeDetectorService` возвращает `DELETE` для DealItem
- Event Store содержит `DealItemDeleted`
- `read_positions.is_active = false`
- Агрегаты сделки пересчитаны (уменьшены)

### 3.3 Сценарии для листов (Sheets)

#### SHEET-ADD: Новый лист (период)

**Как изменить файл:**

- Добавить новый лист с названием нового периода (например "Март 2025")
- Добавить заголовок и данные

**Проверки:**

- Все сделки нового периода созданы
- `read_deals.period_*` соответствует названию листа
- Позиции имеют корректный `period_month`, `period_year`

#### SHEET-RENAME: Переименование листа

**Как изменить файл:**

- Переименовать лист (например "Январь 25" -> "January 2025")

**Проверки:**

- Парсер корректно извлекает Period
- `deal_key` изменяется (это критично!)
- Старые сделки удаляются, новые создаются

#### SHEET-DELETE: Удаление листа

**Как изменить файл:**

- Удалить лист целиком

**Проверки:**

- Все сделки этого периода помечены как удаленные
- Все позиции этих сделок помечены как удаленные

### 3.4 Комплексные сценарии

#### COMPLEX-1: Одновременные изменения

- Добавить новую сделку
- Изменить существующую сделку
- Удалить другую сделку
- Добавить позицию в существующую сделку
- Удалить позицию

#### COMPLEX-2: Перемещение позиции между сделками

- Удалить позицию из одной сделки
- Добавить идентичную в другую

#### COMPLEX-3: Массовые изменения

- 100+ изменений одновременно
- Проверка производительности

#### COMPLEX-4: Идемпотентность

- Повторная синхронизация без изменений
- Не должно быть новых событий

---

## 4. Процесс тестирования (алгоритм)

### Шаг 1: Подготовка базового состояния

```python
# 1.1 Создать базовый Excel файл
base_excel = generator.create_base_file(
    periods=["Январь 2025", "Февраль 2025"],
    deals_per_period=5,
    items_per_deal=3
)

# 1.2 Выполнить начальную синхронизацию
sync_result = orchestrator.execute_sync(base_excel, config)

# 1.3 Сохранить снапшот БД
db_snapshot = verifier.capture_snapshot()
```

### Шаг 2: Генерация сценария

```python
# 2.1 Создать модифицированный файл
modified_excel = scenario_generator.apply_scenario(
    base_excel,
    scenario="DEAL-UPDATE-STATUS",
    params={
        "deal_key": "123|01.01.2025|seller|январь 2025",
        "field": "is_shipped",
        "new_value": "Да"
    }
)

# 2.2 Сохранить ожидаемые изменения
expected_changes = scenario_generator.get_expected_changes()
```

### Шаг 3: Выполнение синхронизации

```python
# 3.1 Запустить инкрементальную синхронизацию
sync_result = orchestrator.execute_sync(modified_excel, incremental_config)

# 3.2 Получить результат детектирования
detection_result = change_detector.detect_changes(...)
```

### Шаг 4: Верификация результатов

```python
# 4.1 Проверить детектирование изменений
verifier.assert_changes_detected(
    actual=detection_result,
    expected=expected_changes
)

# 4.2 Проверить Event Store
verifier.assert_events_created(
    expected_event_types=["DealUpdated"],
    expected_count=1
)

# 4.3 Проверить read-модели
verifier.assert_read_model_updated(
    table="read_deals",
    deal_key="...",
    field="is_shipped_status",
    expected_value="completed"
)

# 4.4 Проверить агрегаты (для позиций)
verifier.assert_totals_recalculated(deal_id="...")
```

---

## 5. Ключевые проверки для каждого теста

| Уровень | Что проверяем | Метод |

|---------|---------------|-------|

| Parser | Корректный парсинг Excel | `ParseResult.deals` |

| ChangeDetector | Тип изменения (INSERT/UPDATE/DELETE) | `ChangeDetectionResult` |

| ChangeDetector | field_changes для UPDATE | `EntityChange.field_changes` |

| EventStore | Создание событий | `SELECT FROM event_store` |

| EventStore | Тип события | `event_type` |

| EventStore | Данные события | `event_data` |

| ReadModel | Обновление записей | `SELECT FROM read_deals/read_positions` |

| ReadModel | Soft delete | `is_active = false` |

| ReadModel | Версионирование | `version` increment |

| ReadModel | Пересчет агрегатов | `calc_*_amount` поля |

| Идемпотентность | Повторный запуск | Нет новых событий |

---

## 6. Инструменты генерации Excel

### ExcelGenerator API

```python
class ExcelGenerator:
    def create_sheet(self, name: str, period: Period) -> Sheet
    def add_deal(self, sheet: Sheet, deal_data: dict) -> int  # returns row
    def add_item(self, sheet: Sheet, row_after: int, item_data: dict) -> int
    def update_cell(self, sheet: Sheet, row: int, col: int, value: Any)
    def delete_row(self, sheet: Sheet, row: int)
    def save(self, path: str)
```

### ScenarioGenerator API

```python
class ScenarioGenerator:
    def apply_deal_insert(self, deal_data: dict) -> ExpectedChanges
    def apply_deal_update(self, deal_key: str, updates: dict) -> ExpectedChanges
    def apply_deal_delete(self, deal_key: str) -> ExpectedChanges
    def apply_item_insert(self, deal_key: str, item_data: dict) -> ExpectedChanges
    def apply_item_update(self, item_key: str, updates: dict) -> ExpectedChanges
    def apply_item_delete(self, item_key: str) -> ExpectedChanges
    def apply_sheet_add(self, period: str) -> ExpectedChanges
    def apply_sheet_delete(self, period: str) -> ExpectedChanges
```

---

## 7. Технологический стек

- Python 3.12
- pytest + pytest-asyncio
- openpyxl (генерация Excel)
- PostgreSQL 16 (Docker)
- SQLAlchemy (async)
- Pydantic
- Loguru