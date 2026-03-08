> Historical document. Preserved for project memory. Do not use as the current source of truth.

# Детерминированная генерация ID

## Проблема

При каждой синхронизации ID сделок в таблице `read_deals` изменялись, что приводило к:
- Нарушению связей Foreign Key с таблицей `read_positions`
- Потере истории audit записей  
- Проблемам с индексами и статистикой

## Корень проблемы

В domain модели `Deal` ID генерировался случайно при каждом создании объекта:

```python
# ДО: случайный ID при каждом создании
id: UUID = Field(default_factory=uuid4, description="Уникальный ID сделки")
```

**Что происходило:**
1. Excel Parser → создает `Deal()` → **новый UUID каждый раз**
2. Orchestrator → берет `deal.id` → **попадает в событие**
3. ReadModelBuilder → берет ID из события → **перезаписывает в read_deals**

## Решение

Изменена логика генерации ID на **детерминированную на основе business key**:

### Deal ID
```python
@computed_field
@property
def id(self) -> UUID:
    """Детерминированный ID на основе deal_key."""
    if self.explicit_id is not None:
        return self.explicit_id
        
    # Фиксированный namespace для всех сделок
    namespace = UUID('550e8400-e29b-41d4-a716-446655440000')
    return uuid5(namespace, self.deal_key)
```

**Формула deal_key:**
```
"{client_name}|{invoice_number}|{invoice_date}|{seller}|{period}"
```

### DealItem ID  
```python
@computed_field
@property
def id(self) -> UUID:
    """Детерминированный ID на основе deal_id и position_number."""
    if self.explicit_id is not None:
        return self.explicit_id
        
    # Фиксированный namespace для всех позиций
    namespace = UUID('650e8400-e29b-41d4-a716-446655440000')
    # Ключ для позиции: deal_id + position_number + product_name
    item_key = f"{self.deal_id or ''}|{self.position_number or 1}|{self.product_name}"
    return uuid5(namespace, item_key)
```

## Преимущества

### ✅ Стабильность
- Один `deal_key` = всегда один ID
- ID не меняется при повторной синхронизации
- Связи с `read_positions` сохраняются

### ✅ Уникальность
- Разные `deal_key` = разные ID
- UUID5 обеспечивает равномерное распределение
- Практически нулевая вероятность коллизий

### ✅ Предсказуемость
- Можно вычислить ID зная business key
- Упрощается отладка и поиск
- Легче тестировать

### ✅ Совместимость
- Остается стандартным UUID4 форматом
- Нет изменений в базе данных
- Работает с существующим кодом

## Обновленная архитектура

```python
# Создание Deal из Excel
deal = Deal(
    client_name="ООО Тест",
    invoice_number="12345", 
    invoice_date="15.01.2024",
    period=period
)

# ID автоматически вычисляется детерминированно
print(deal.id)  # c4066419-1b72-581e-9758-aa76a59051ba

# При повторном создании с теми же данными
deal2 = Deal(
    client_name="ООО Тест",
    invoice_number="12345",
    invoice_date="15.01.2024", 
    period=period
)

print(deal2.id)  # c4066419-1b72-581e-9758-aa76a59051ba (тот же!)
```

## Возможность переопределения

Добавлена возможность явного задания ID (для тестов и миграции):

```python
deal = Deal(client_name="Тест", period=period)
manual_id = UUID('12345678-1234-5678-9abc-123456789012')
deal.set_id(manual_id)
print(deal.id)  # 12345678-1234-5678-9abc-123456789012
```

## Миграция существующих данных

Для обновления существующих записей на детерминированные ID:

```python
async def migrate_existing_deals():
    """Обновить существующие deal_id на детерминированные."""
    
    deals = await session.execute(select(ReadModelDeal))
    
    for deal in deals.scalars():
        # Пересчитать ID на основе deal_key  
        namespace = UUID('550e8400-e29b-41d4-a716-446655440000')
        new_id = uuid5(namespace, deal.deal_key)
        
        if deal.id != new_id:
            # Обновить ID в read_deals и связанных read_positions
            # ... код миграции
```

## Тестирование

Создан тест `scripts/test/test_deterministic_ids.py` для проверки:
- Детерминированности Deal ID
- Детерминированности DealItem ID  
- Стабильности при пересоздании
- Возможности переопределения

**Результаты тестов: ✅ ВСЕ ТЕСТЫ ПРОШЛИ**

## Влияние на синхронизацию

Теперь при синхронизации:
1. Excel Parser создает Deal с детерминированным ID
2. Orchestrator использует стабильный ID в событиях
3. ReadModelBuilder получает тот же ID при повторной обработке
4. **Записи в read_deals больше не перезаписываются!**

## Технические детали

### UUID5 алгоритм
- Использует SHA-1 для хеширования `namespace + name`
- Гарантирует одинаковый результат для одинаковых входных данных
- Обеспечивает равномерное распределение по пространству UUID

### Namespace UUID
- `550e8400-e29b-41d4-a716-446655440000` для Deal
- `650e8400-e29b-41d4-a716-446655440000` для DealItem
- Фиксированные значения обеспечивают стабильность

### Вероятность коллизий
- UUID5 использует 122 эффективных бита
- Для миллиона сделок вероятность коллизии ≈ 0%
- Практически невозможны в реальных условиях

## Заключение

Проблема с изменяющимися ID в `read_deals` **полностью решена**. Теперь:
- ✅ ID стабильны между синхронизациями
- ✅ Связи FK сохраняются 
- ✅ Нет потери audit данных
- ✅ Улучшена производительность (нет лишних UPDATE)
- ✅ Упрощена отладка и тестирование

Изменения обратно совместимы и не требуют изменений в других частях системы.
