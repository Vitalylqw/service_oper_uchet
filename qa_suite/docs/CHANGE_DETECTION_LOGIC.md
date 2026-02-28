# Логика детектирования изменений

## 1. Обзор

Система детектирования изменений сравнивает данные из Excel файла с текущим состоянием БД и определяет какие операции необходимо выполнить:
- INSERT - новые сущности
- UPDATE - измененные сущности  
- DELETE - удаленные сущности

## 2. Компоненты

### 2.1 ChangeDetectorService

Основной сервис детектирования (`src/application/change_detector/detector.py`):

```python
class ChangeDetectorService:
    async def detect_changes(
        self, excel_deals: list[Deal], sync_period_months: int = 3
    ) -> ChangeDetectionResult
```

### 2.2 ChangeDetectionResult

Результат детектирования (`src/application/change_detector/models.py`):

```python
class ChangeDetectionResult:
    insertions: list[EntityChange]  # Новые сущности
    updates: list[EntityChange]     # Измененные сущности
    deletions: list[EntityChange]   # Удаленные сущности
```

### 2.3 EntityChange

Описание одного изменения:

```python
class EntityChange:
    change_type: ChangeType      # INSERT, UPDATE, DELETE
    entity_type: EntityType      # DEAL, DEAL_ITEM
    entity_key: str              # Бизнес-ключ сущности
    field_changes: dict          # Изменения полей (для UPDATE)
    old_entity: Any              # Старое состояние
    new_entity: Any              # Новое состояние
    old_hash: str                # Хэш до изменения
    new_hash: str                # Хэш после изменения
```

## 3. Алгоритм детектирования

### 3.1 Подготовка

1. Парсинг Excel файла -> список Deal объектов
2. Загрузка текущих данных из БД для соответствующих периодов
3. Построение hash-кэшей для быстрого сравнения

### 3.2 Сравнение сделок

```
Для каждой сделки из Excel:
    deal_key = генерация_ключа(invoice_number, invoice_date, seller, period)
    
    Если deal_key НЕ существует в БД:
        -> INSERT (новая сделка)
    Иначе:
        Если hash(excel_deal) != hash(db_deal):
            -> UPDATE (изменения в полях)
        Иначе:
            -> БЕЗ ИЗМЕНЕНИЙ

Для каждой сделки из БД:
    Если deal_key НЕ существует в Excel:
        -> DELETE (сделка удалена)
```

### 3.3 Сравнение позиций

Аналогично сделкам, но используется `item_key`:

```python
item_key = get_full_hash_key(deal_key).value
# Включает: position_number, product_name, все финансовые поля
```

## 4. Хэширование

### 4.1 Deal Hash

Поля для хэширования сделки:

```python
deal_dict = {
    "invoice_info": str,
    "period_full_name": str,
    "upd_number": str,
    "is_shipped": str,
    "is_paid": str,
    "seller": str,
    "total_revenue_amount": Decimal,
    "total_margin_amount": Decimal,
    "total_cost_amount": Decimal,
    "kickback_amount_value": Decimal,
    "items_count": int,
    "total_quantity": Decimal,
}
hash_key = HashKey.from_dict(deal_dict)
```

### 4.2 DealItem Hash

Поля для хэширования позиции:

```python
item_dict = {
    "position_number": str,
    "product_name": str,
    "supplier_name": str,
    "pickup_date": str,
    "quantity": str,
    "purchase_price": str,
    "sale_price": str,
    "revenue": str,
    "margin": str,
    "cost": str,
    "deal_key": str,
}
hash_key = HashKey.from_dict(item_dict)
```

## 5. События

После детектирования изменений создаются события:

| Изменение | Событие |
|-----------|---------|
| INSERT Deal | DealCreated |
| INSERT DealItem | DealItemAdded |
| UPDATE Deal | DealUpdated |
| UPDATE DealItem | DealItemUpdated |
| DELETE Deal | DealDeleted |
| DELETE DealItem | DealItemDeleted |

## 6. Обновление Read-моделей

ReadModelBuilder обрабатывает события и обновляет таблицы:

- `read_deals` - сделки
- `read_positions` - позиции товаров

## 7. Особенности реализации

### 7.1 Идемпотентность

При повторной синхронизации того же файла:
- Хэши совпадают -> изменений нет
- result.has_changes == False

### 7.2 Каскадное удаление

При удалении сделки автоматически удаляются все её позиции через CASCADE constraint в БД.

### 7.3 Нормализация данных

Перед сравнением данные нормализуются:
- Строки: strip() + lower()
- Числа: приведение к Decimal с заданной точностью
- Статусы: конвертация в enum Status

## 8. Диаграмма процесса

```
Excel File
    |
    v
[ExcelParserService]
    |
    v
List[Deal] (parsed)
    |
    v
[ChangeDetectorService]
    |
    +---> Load DB Deals by periods
    |
    +---> Build hash caches
    |
    +---> Compare deals & items
    |
    v
ChangeDetectionResult
    |
    v
[SyncOrchestratorService]
    |
    +---> Create Events
    |
    +---> Store in event_store
    |
    v
[ReadModelBuilder]
    |
    +---> Process events
    |
    +---> Update read_deals
    |
    +---> Update read_positions
    |
    v
Updated Database
```
