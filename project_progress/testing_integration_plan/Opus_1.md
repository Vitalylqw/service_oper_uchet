# План полномасштабного интеграционного тестирования Change Detection

## 1. Анализ структуры Excel файла

### 1.1 Структура книги Excel

- **Каждый лист = один период** (месяц + год)
- Название листа парсится как период: `"Май 2025"`, `"Январь 2024"`
- Добавление/удаление листа = добавление/удаление данных за период

### 1.2 Структура данных на листе

**Строка заголовков** (обнаруживается по наличию "Клиент"):

| Индекс | Название | Описание |

|--------|----------|----------|

| 0 | Клиент | Название клиента |

| 1 | Счет | Информация о счете (номер + дата) |

| 2 | Отгружен | Статус отгрузки ("да"/"нет") |

| 3 | УПД | Номер УПД |

| 4 | Оплачен | Статус оплаты ("да"/"нет") |

| 5 | Выручка | Общая выручка по сделке |

| 6 | Маржа | Общая маржа по сделке |

| 7 | Продавец | Имя продавца |

| 8 | Себест. | Общая себестоимость |

| 9 | Откат | Сумма отката |

**Master-запись (Deal)** - строка с заполненным "Клиент":

```
| ЛЕНТЕХСТРОЙ | 5938 от 16.06.2025 | нет | | нет | 145270 | 29713.68 | КРЕПЕЖ-ИНСТРУМЕНТ ООО | 30536.32 | |
```

**Detail-записи (DealItem)** - строки с пустым "Клиент":

```
| | Нож строительный КВТ | 20 | 100.50 | 356 | 7120 | 2840 | | 1005 | этм | 18 |
```

Индексы для DealItem:

| Индекс | Поле | Описание |

|--------|------|----------|

| 1 | product_name | Название товара |

| 2 | quantity | Количество |

| 3 | purchase_price | Цена закупки (5 знаков) |

| 4 | sale_price | Цена продажи |

| 5 | revenue | Выручка позиции |

| 6 | margin | Маржа позиции |

| 8 | cost | Себестоимость позиции |

| 9 | supplier_name | Поставщик |

| 10 | pickup_date | Дата забора |

### 1.3 Ключевые идентификаторы

**deal_key** (уникальный ключ сделки):

```python
deal_key = f"{invoice_number}|{invoice_date}|{seller}|{period}".lower()
# Пример: "5938|16.06.2025|крепеж-инструмент ооо|май 2025"
```

**Идентификация позиции** (item_key):

```python
item_key = get_full_hash_key(deal_key)  # hash от position_number + product_name + deal_key + все финансовые поля
```

---

## 2. Категории тестовых сценариев

### 2.1 INSERT операции (новые данные)

#### TEST_INS_01: Добавление нового листа (новый период)

**Изменение в Excel:**

- Добавить новый лист "Июнь 2025" с 2 сделками и 5 позициями

**Ожидаемый результат:**

- ChangeDetectionResult.insertions содержит 2 Deal + 5 DealItem
- Events: 2x DealCreated + 5x DealItemAdded
- БД: 2 записи в read_deals, 5 записей в read_positions
- Период "Июнь 2025" появился в системе

**Проверки:**

```python
assert result.insertion_count == 7  # 2 deals + 5 items
assert db.count_deals_by_period("Июнь", "2025") == 2
assert db.count_positions_by_period("Июнь", "2025") == 5
```

#### TEST_INS_02: Добавление новой сделки в существующий период

**Изменение в Excel:**

- В лист "Май 2025" добавить нового клиента с 3 позициями

**Ожидаемый результат:**

- ChangeDetectionResult.insertions содержит 1 Deal + 3 DealItem
- Существующие сделки НЕ затронуты

**Проверки:**

```python
assert result.insertion_count == 4
assert db.deal_exists(new_deal_key) == True
assert db.get_deal(existing_deal_key).updated_at == original_updated_at  # не изменился
```

#### TEST_INS_03: Добавление новых позиций к существующей сделке

**Изменение в Excel:**

- К существующей сделке "ЛЕНТЕХСТРОЙ | 5938" добавить 2 новых товара

**Ожидаемый результат:**

- ChangeDetectionResult.insertions содержит 2 DealItem
- Deal НЕ в insertions (но может быть в updates из-за изменения items_count)
- position_number у новых позиций = max(existing) + 1, +2

**Проверки:**

```python
assert result.insertion_count == 2  # только items
assert db.get_deal(deal_key).items_count == original_count + 2
assert db.get_positions_by_deal(deal_key)[-1].position_number == original_max + 2
```

---

### 2.2 UPDATE операции (изменение данных)

#### TEST_UPD_01: Изменение статусов сделки (is_shipped, is_paid)

**Изменение в Excel:**

- Сделка "5938": Отгружен "нет" -> "да", Оплачен "нет" -> "да"

**Ожидаемый результат:**

- ChangeDetectionResult.updates содержит 1 Deal с field_changes
- field_changes = {"is_shipped": {"old": "pending", "new": "completed"}, "is_paid": {...}}
- Event: DealUpdated

**Проверки:**

```python
assert result.update_count == 1
assert "is_shipped" in result.updates[0].field_changes
assert db.get_deal(deal_key).is_shipped == "completed"
```

#### TEST_UPD_02: Изменение финансовых показателей сделки

**Изменение в Excel:**

- Изменить total_revenue: 145270 -> 150000
- Изменить total_margin: 29713.68 -> 32000

**Ожидаемый результат:**

- ChangeDetectionResult.updates содержит 1 Deal
- field_changes содержит total_revenue, total_margin
- hash_key сделки изменился

**Проверки:**

```python
assert result.updates[0].old_hash != result.updates[0].new_hash
assert db.get_deal(deal_key).total_revenue_amount == Decimal("150000.00")
```

#### TEST_UPD_03: Изменение данных позиции (quantity, prices)

**Изменение в Excel:**

- Позиция "Нож строительный": quantity 20 -> 25, purchase_price 100.50 -> 110.00

**Ожидаемый результат:**

- ChangeDetectionResult.updates содержит 1 DealItem
- Event: DealItemUpdated
- Пересчитаны revenue, margin, cost (автоматически через validators)

**Проверки:**

```python
assert result.update_count >= 1  # item updated
item_update = [u for u in result.updates if u.entity_type == EntityType.DEAL_ITEM][0]
assert "quantity" in item_update.field_changes
assert db.get_position(item_id).quantity == Decimal("25")
# Проверка автоматического пересчета
assert db.get_position(item_id).cost_amount == Decimal("2750.00")  # 25 * 110
```

#### TEST_UPD_04: Изменение product_name позиции

**Изменение в Excel:**

- "Нож строительный КВТ" -> "Нож строительный КВТ НСМ-02 78492"

**Ожидаемый результат:**

- Старая позиция DELETE + новая позиция INSERT (т.к. hash_key изменился)
- ИЛИ UPDATE с изменением hash_key (зависит от реализации)

**Проверки:**

```python
# Вариант A: delete + insert
assert result.deletion_count == 1 and result.insertion_count == 1
# Вариант B: update
assert result.update_count == 1 and "product_name" in result.updates[0].field_changes
```

#### TEST_UPD_05: Изменение supplier_name позиции

**Изменение в Excel:**

- Поставщик "этм" -> "ЭТМ Групп"

**Ожидаемый результат:**

- ChangeDetectionResult.updates содержит 1 DealItem
- hash_key позиции изменился

**Проверки:**

```python
assert db.get_position_by_deal_and_pos(deal_key, pos_num).supplier_name == "ЭТМ Групп"
```

---

### 2.3 DELETE операции (удаление данных)

#### TEST_DEL_01: Удаление листа (целого периода)

**Изменение в Excel:**

- Удалить лист "Май 2025"

**Ожидаемый результат:**

- Все сделки периода в deletions
- Events: DealDeleted для каждой сделки
- В БД: записи удалены (hard delete через CASCADE)

**Проверки:**

```python
assert result.deletion_count == original_deals_in_may + original_items_in_may
assert db.count_deals_by_period("Май", "2025") == 0
assert db.count_positions_by_period("Май", "2025") == 0
```

#### TEST_DEL_02: Удаление сделки из периода

**Изменение в Excel:**

- Удалить строку клиента "ЛЕНТЕХСТРОЙ | 5938" и все его позиции

**Ожидаемый результат:**

- ChangeDetectionResult.deletions содержит 1 Deal + N DealItems
- Event: DealDeleted (CASCADE удалит позиции)

**Проверки:**

```python
deal_items_count = original_items_for_deal
assert result.deletion_count == 1 + deal_items_count
assert db.deal_exists(deal_key) == False
```

#### TEST_DEL_03: Удаление позиций из сделки (частичное)

**Изменение в Excel:**

- Из сделки "5938" удалить 3 из 12 позиций

**Ожидаемый результат:**

- ChangeDetectionResult.deletions содержит 3 DealItem
- Deal НЕ удаляется, но items_count обновляется

**Проверки:**

```python
assert result.deletion_count == 3
assert db.get_deal(deal_key).items_count == original_count - 3
assert db.deal_exists(deal_key) == True
```

#### TEST_DEL_04: Удаление всех позиций из сделки

**Изменение в Excel:**

- Удалить все позиции товаров, оставить только строку Deal

**Ожидаемый результат:**

- Все позиции в deletions
- Deal остается, но items_count = 0
- calc_revenue/margin/cost = 0

**Проверки:**

```python
assert db.get_deal(deal_key).items_count == 0
assert db.get_deal(deal_key).calc_revenue_amount == Decimal("0")
```

---

### 2.4 Смешанные операции (MIXED)

#### TEST_MIX_01: INSERT + UPDATE в одном периоде

**Изменение в Excel:**

- Добавить новую сделку с 2 позициями
- Изменить статус существующей сделки

**Ожидаемый результат:**

- insertions: 1 Deal + 2 DealItems
- updates: 1 Deal

**Проверки:**

```python
assert result.insertion_count == 3
assert result.update_count == 1
```

#### TEST_MIX_02: UPDATE + DELETE в одной сделке

**Изменение в Excel:**

- Изменить quantity одной позиции
- Удалить другую позицию

**Ожидаемый результат:**

- updates: 1 DealItem
- deletions: 1 DealItem

#### TEST_MIX_03: INSERT + UPDATE + DELETE (полный цикл)

**Изменение в Excel:**

- Добавить новый лист с 1 сделкой
- Изменить данные существующей сделки в другом периоде
- Удалить третью сделку

**Ожидаемый результат:**

- insertions > 0
- updates > 0
- deletions > 0

---

### 2.5 Edge Cases (граничные случаи)

#### TEST_EDGE_01: Идемпотентность (повторная синхронизация без изменений)

**Действие:** Загрузить тот же файл дважды

**Ожидаемый результат:**

- При второй загрузке: insertions=0, updates=0, deletions=0
- hash_key всех сущностей идентичны

**Проверки:**

```python
assert result.total_changes == 0
assert result.has_changes == False
```

#### TEST_EDGE_02: Пустой Excel файл

**Изменение в Excel:** Файл без данных (только заголовки)

**Ожидаемый результат:**

- Все существующие данные в deletions
- БД очищена для соответствующих периодов

#### TEST_EDGE_03: Файл с формулами

**Изменение в Excel:** Изменить значение ячейки, от которой зависят формулы

**Ожидаемый результат:**

- Формулы пересчитаны парсером (xlcalculator)
- Изменения в расчетных полях детектируются

#### TEST_EDGE_04: Большой файл (100+ сделок, 1000+ позиций)

**Действие:** Загрузить файл с большим объемом данных

**Ожидаемый результат:**

- Синхронизация завершена успешно
- Время выполнения < 60 секунд
- Память не превышает лимит

**Проверки:**

```python
assert result.summary.duration_seconds < 60
assert result.summary.success == True
```

#### TEST_EDGE_05: Дубликаты deal_key

**Изменение в Excel:** Две сделки с одинаковым номером счета/датой/продавцом

**Ожидаемый результат:**

- Вторая сделка должна обрабатываться как UPDATE первой (или ошибка)
- Поведение зависит от бизнес-логики

#### TEST_EDGE_06: Null/пустые значения в обязательных полях

**Изменение в Excel:** Оставить пустым client_name или invoice_info

**Ожидаемый результат:**

- Ошибка парсинга для конкретной строки
- Остальные данные обработаны

#### TEST_EDGE_07: Специальные символы в названиях

**Изменение в Excel:** Клиент = `ООО "Тест & Ко <>"`, товар = `Товар #1 @100%`

**Ожидаемый результат:**

- Данные сохранены корректно
- hash_key вычислен правильно

---

## 3. Структура тестового проекта

```
tests/integration_full/
├── conftest.py                    # DB fixtures, cleanup, базовые хелперы
├── fixtures/
│   └── excel/
│       ├── base_state.xlsx        # Исходное состояние (V1) - 2 периода, 5 сделок, 30 позиций
│       ├── generators/
│       │   └── excel_builder.py   # Программная генерация Excel файлов
│       └── scenarios/
│           ├── ins_01_new_sheet.xlsx
│           ├── ins_02_new_deal.xlsx
│           ├── ins_03_new_items.xlsx
│           ├── upd_01_status_change.xlsx
│           ├── upd_02_financial_change.xlsx
│           ├── upd_03_item_quantity.xlsx
│           ├── upd_04_product_name.xlsx
│           ├── upd_05_supplier.xlsx
│           ├── del_01_remove_sheet.xlsx
│           ├── del_02_remove_deal.xlsx
│           ├── del_03_partial_items.xlsx
│           ├── del_04_all_items.xlsx
│           ├── mix_01_insert_update.xlsx
│           ├── mix_02_update_delete.xlsx
│           ├── mix_03_full_cycle.xlsx
│           ├── edge_01_idempotent.xlsx      # копия base_state
│           ├── edge_02_empty.xlsx
│           ├── edge_04_large.xlsx
│           ├── edge_05_duplicate_key.xlsx
│           ├── edge_06_null_required.xlsx
│           └── edge_07_special_chars.xlsx
├── helpers/
│   ├── excel_builder.py           # Класс для создания/модификации Excel
│   ├── db_state.py                # Проверка состояния БД
│   └── assertions.py              # Кастомные assert-функции
├── test_insert_operations.py      # TEST_INS_01 - TEST_INS_03
├── test_update_operations.py      # TEST_UPD_01 - TEST_UPD_05
├── test_delete_operations.py      # TEST_DEL_01 - TEST_DEL_04
├── test_mixed_operations.py       # TEST_MIX_01 - TEST_MIX_03
├── test_edge_cases.py             # TEST_EDGE_01 - TEST_EDGE_07
└── run_all_tests.bat              # Скрипт запуска всех тестов
```

---

## 4. Порядок выполнения тестов

1. **Setup:** Очистка БД -> Загрузка base_state.xlsx -> Проверка baseline
2. **Для каждого теста:**

   - Загрузка сценарного файла
   - Выполнение sync_orchestrator.execute_sync()
   - Проверка ChangeDetectionResult
   - Проверка состояния БД
   - Откат к baseline (или полная очистка)

---

## 5. Ключевые таблицы БД для проверки

| Таблица | Что проверять |

|---------|---------------|

| `read_deals` | deal_key, hash_key, items_count, total_*, calc_*, has_totals_error |

| `read_positions` | deal_id, position_number, hash_key, quantity, *_amount |

| `event_store` | event_type, event_data, processed_at |

| `read_audit` | entity_type, change_type, field_name, old/new_value |

---

## 6. Примерная реализация теста

```python
@pytest.mark.asyncio
async def test_ins_02_new_deal_in_existing_period(
    sync_orchestrator, db_session, load_base_state
):
    """TEST_INS_02: Добавление новой сделки в существующий период."""
    # Arrange
    original_deals_count = await db_session.scalar(
        select(func.count()).select_from(ReadModelDeal)
        .where(ReadModelDeal.period_full_name == "Май 2025")
    )
    
    # Act
    result = await sync_orchestrator.execute_sync(
        "fixtures/excel/scenarios/ins_02_new_deal.xlsx",
        SyncConfiguration(sync_type="full", create_events=True)
    )
    
    # Assert - ChangeDetectionResult
    assert result.summary.success == True
    assert result.change_detection_result.insertion_count == 4  # 1 deal + 3 items
    assert result.change_detection_result.update_count == 0
    assert result.change_detection_result.deletion_count == 0
    
    # Assert - Database state
    new_deals_count = await db_session.scalar(
        select(func.count()).select_from(ReadModelDeal)
        .where(ReadModelDeal.period_full_name == "Май 2025")
    )
    assert new_deals_count == original_deals_count + 1
    
    # Assert - Events created
    new_deal_events = [e for e in result.events_created if e["event_type"] == "DealCreated"]
    assert len(new_deal_events) == 1
```