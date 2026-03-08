> Historical document. Preserved for project memory. Do not use as the current source of truth.

# План миграции на hash_key для уникальности позиций

## Цель
Заменить составные ключи (`position_key`) на `hash_key` для обеспечения истинной уникальности позиций в системе.

## Анализ текущей ситуации

### Проблемы с текущими ключами:

1. **Несогласованность алгоритмов:**
   - ChangeDetector: `f"{deal.deal_key}|{item.product_name}|{item.supplier_name or ''}"`
   - ReadModelBuilder: `f"{item.product_name}|{item.supplier_name}|{sale_price_str}"`

2. **Неполная уникальность position_key:**
   - НЕ учитывает: quantity, pickup_date, purchase_price, revenue, margin, cost
   - Возможны конфликты при одинаковом товаре с разными параметрами

3. **Потенциальные дубликаты:**
   - Одинаковый товар + поставщик + цена, но разное количество
   - Одинаковый товар с пустым поставщиком

### Преимущества hash_key:

✅ **Уже реализовано и работает:**
- HashKey.from_dict() учитывает ВСЕ поля позиции
- MD5 hash от всех значимых полей
- Уже сохраняется в БД и проиндексирован

✅ **Истинная уникальность:**
- Изменение любого поля → новый hash
- Невозможны ложные дубликаты
- Согласованность во всей системе

## План реализации

### Этап 1: Подготовка миграции БД
**Файлы:** `scripts/database/migrations/`

1. Создать миграцию `YYYYMMDD_replace_position_key_with_hash.py`
2. Добавить новый unique constraint: `(deal_id, hash_key)`
3. Удалить старый constraint: `(deal_id, position_key)`
4. Сохранить position_key как обычное поле (для совместимости)

### Этап 2: Изменение Change Detector
**Файлы:** `src/application/change_detector/detector.py`

**БЫЛО:**
```python
def _get_item_key(self, deal: Deal, item: DealItem) -> str:
    return f"{deal.deal_key}|{item.product_name}|{item.supplier_name or ''}"
```

**СТАНЕТ:**
```python
def _get_item_key(self, deal: Deal, item: DealItem) -> str:
    return item.hash_key.value  # Используем hash вместо составного ключа
```

### Этап 3: Изменение Read Model Builder
**Файлы:** `src/infrastructure/workers/read_model_builder.py`

**БЫЛО:**
```python
stmt = stmt.on_conflict_do_update(
    index_elements=["deal_id", "position_key"],
    set_=update_columns,
)
```

**СТАНЕТ:**
```python
stmt = stmt.on_conflict_do_update(
    index_elements=["deal_id", "hash_key"],
    set_=update_columns,
)
```

### Этап 4: Обновление тестов
**Файлы:** `tests/unit/application/test_change_detector.py`

- Обновить тесты `_get_item_key`
- Убедиться что hash генерируется корректно
- Протестировать unique constraint

### Этап 5: Тестирование
**Сценарии:**

1. **Создание позиций** - hash как ключ уникальности
2. **Обновление позиций** - изменение любого поля → новый hash
3. **Удаление позиций** - корректная работа change detection
4. **Конфликты** - проверка unique constraint на hash
5. **Миграция данных** - существующие данные сохраняются

## Оценка рисков

### 🟡 Средние риски:
1. **Изменение unique constraint** - может повлиять на существующие данные
2. **Изменение логики ключей** - нужно убедиться в корректности

### 🟢 Низкие риски:
1. **hash_key уже вычисляется** - нет новой логики
2. **Индекс уже существует** - нет проблем с производительностью
3. **Обратная совместимость** - position_key остается в БД

### Митигация рисков:
- ✅ Резервное копирование БД перед миграцией
- ✅ Поэтапное развертывание с тестированием
- ✅ Возможность rollback через обратную миграцию

## Ожидаемые результаты

### После миграции:
1. **Устранение ложных дубликатов** позиций
2. **Согласованность ключей** во всех модулях
3. **Более надежная change detection**
4. **Упрощение логики** уникальности

### Метрики успеха:
- 0 конфликтов unique constraint
- Корректная работа синхронизации
- Все тесты проходят
- Производительность не ухудшилась

## Следующие шаги
1. Создать миграцию БД
2. Изменить Change Detector
3. Изменить Read Model Builder  
4. Обновить тесты
5. Провести полное тестирование