# АРХИТЕКТУРНОЕ РЕВЬЮ СИСТЕМЫ СИНХРОНИЗАЦИИ

**Автор:** Системный архитектор  
**Дата:** 29 ноября 2025  
**Документ-основа:** SYNC_ANALYSIS_PLAN.md  
**Статус:** Критический анализ

---

## 1. EXECUTIVE SUMMARY

### 1.1 Общая оценка плана

План анализа выполнен на **высоком профессиональном уровне**. Детальность проработки, структурированность подхода и критичность мышления заслуживают высокой оценки. Автор плана продемонстрировал:

- Глубокое понимание Event Sourcing и CQRS паттернов
- Системное мышление при анализе многослойной архитектуры
- Практический подход к выявлению проблем
- Корректную приоритизацию задач

**Оценка плана: 9/10**

### 1.2 Подтверждение критических находок

После детального изучения кодовой базы подтверждаю:

| Находка | Статус | Критичность | Оценка точности |
|---------|--------|-------------|-----------------|
| BUG-001: Audit не создается | ✅ ПОДТВЕРЖДЕН | КРИТИЧЕСКАЯ | 100% |
| BUG-002: has_totals_error с NULL | ✅ ПОДТВЕРЖДЕН | КРИТИЧЕСКАЯ | 100% |
| BUG-003: deal_key mismatch риск | ⚠️ ТРЕБУЕТ ПРОВЕРКИ | СРЕДНЯЯ | 80% |

### 1.3 Критическое замечание

**Основная слабость проекта:** Отсутствие автоматизированного тестирования для критичных компонентов (change_detector, read_model_builder). При такой сложности архитектуры это создает высокие риски регрессии.

---

## 2. АРХИТЕКТУРНЫЙ АНАЛИЗ

### 2.1 Оценка архитектуры проекта

#### ✅ Сильные стороны

**1. Правильное применение DDD паттернов**
- Четкое разделение на Domain/Application/Infrastructure слои
- Value Objects (Money, Period, HashKey) с инвариантами
- Агрегат Deal с границами консистентности
- Builders для сложных объектов

**2. Event Sourcing реализован корректно**
- События хранят полную историю изменений
- Sequence number для упорядочивания
- Upcasting для эволюции схемы
- Детерминированные UUID через uuid5

**3. CQRS разделение**
- Write models (events) отделены от read models
- Оптимизированные read models для запросов
- Асинхронная обработка событий

**4. Продуманные оптимизации**
- Hash-based change detection (быстрое сравнение)
- Индексы на hash_key и deal_key
- Пакетная обработка событий

#### ⚠️ Слабые стороны

**1. Отсутствие транзакционной целостности**

```python
# src/infrastructure/workers/simple_position_sync.py:193
async def _upsert_position(...):
    # ...
    await self.session.commit()  # ❌ Коммит внутри метода
```

**Проблема:** Метод вызывается в цикле, создавая множество мелких транзакций. При падении в середине обработки получаем partial update без возможности rollback всей операции.

**Рекомендация:** Убрать commit, делегировать управление транзакциями вызывающему коду.

**2. Смешение ответственностей в ReadModelBuilder**

`ReadModelBuilder` выполняет слишком много:
- Обработка событий (бизнес-логика)
- Пересчет агрегатов (domain logic)
- UPSERT в БД (infrastructure)
- Маршрутизация событий (application logic)
- Управление отложенными событиями

**Рекомендация:** Разделить на:
- `EventHandler` (обработка событий)
- `AggregateRecalculator` (пересчет totals)
- `ReadModelRepository` (персистентность)

**3. Deferred events - потенциальная проблема**

```python
# Если DealItemAdded приходит раньше DealCreated
await deferred_queue.add_event(event, reason="parent_not_found")
```

**Проблема:** Нет гарантии, что отложенные события когда-либо обработаются. Нет механизма очистки устаревших.

**Рекомендация:** 
- Dead letter queue с TTL
- Периодический retry с экспоненциальным backoff
- Мониторинг размера очереди

### 2.2 Оценка flow данных

Поток данных в целом **архитектурно правильный**:

```
Excel → Parser → Domain Models → Change Detector → 
→ Orchestrator → Events → Event Store → 
→ Read Model Builder → Read Models (PostgreSQL)
```

**Критические точки (из плана):**

#### [A] Parser → ChangeDetector ✅ КОРРЕКТНО
- hash_key вычисляется детерминированно
- Нормализация строк (strip, lower) применяется везде
- Decimal precision сохраняется

#### [B] ChangeDetector → Orchestrator ⚠️ ТРЕБУЕТ ПРОВЕРКИ
- Логика change detection **выглядит правильно**
- Используется deal_key для сравнения
- Hash comparison для быстрого определения изменений

**Гипотеза о причине проблемы "все как INSERT":**
```python
# src/application/change_detector/detector.py:131
period_deals = await self.deal_repository.find_by_period(month, year)
```

Если `find_by_period` возвращает пустой список (БД пустая или период не найден), **ВСЕ** excel_deals будут помечены как INSERT.

**Это нормальное поведение при первом запуске!**

Но если при повторном запуске все еще INSERT - проблема в:
1. period_month/period_year не совпадают между Excel и БД
2. deal_key генерируется по-разному при парсинге и загрузке

#### [C] Orchestrator → EventStore ✅ КОРРЕКТНО
- События создаются только для detected changes
- Если [B] возвращает все как INSERT, здесь будут лишние события

#### [D] EventStore → ReadModelBuilder ✅ КОРРЕКТНО
- Читает события с `processed_at IS NULL`
- Маршрутизация по event_type правильная

#### [E] ReadModelBuilder → Database ❌ КРИТИЧЕСКИЕ БАГИ
- ✅ UPSERT логика правильная
- ❌ has_totals_error при NULL - НЕПРАВИЛЬНАЯ (BUG-002)
- ❌ audit не заполняется - return перед кодом (BUG-001)

---

## 3. ДЕТАЛЬНЫЙ АНАЛИЗ БАГОВ

### 3.1 BUG-001: Audit не создается [ПОДТВЕРЖДЕН]

**Файл:** `src/infrastructure/workers/read_model_builder.py:1225`

```python
async def _create_audit_entry(...):
    try:
        # Логирование
        if additional_data:
            logger.debug(...)
        else:
            logger.debug(...)
        return  # ❌ БАГ: Код ниже недостижим
        
        audit_entry = ReadModelAudit(...)  # Никогда не выполнится
        self.session.add(audit_entry)
```

**Анализ:**
- Очевидная ошибка - `return` оставлен после замены создания audit на логирование
- Таблица `read_audit` пустая - это объясняет проблему из TODO.MD
- Код создания записи синтаксически правильный, но недостижимый

**Приоритет исправления:** НЕМЕДЛЕННО (5 минут работы)

**Риски исправления:** НУЛЕВЫЕ - просто удалить `return`

### 3.2 BUG-002: has_totals_error с NULL [ПОДТВЕРЖДЕН]

**Файл:** `src/infrastructure/workers/read_model_builder.py:1183-1189`

**Текущая логика (НЕПРАВИЛЬНАЯ):**
```python
def _delta(src: Decimal | None, calc: Decimal) -> Decimal:
    return abs((src or Decimal("0")) - calc)  # NULL → 0

has_error = any(
    _delta(val, calc) > Decimal("0.01")
    for val, calc in ((src_rev, rev), (src_mar, mar), (src_cost, cost))
)
```

**Проблема:**
- `total_revenue = NULL` (режим no_cash) превращается в `0`
- `calc_revenue = 1000` (сумма позиций)
- `_delta(NULL, 1000) = 1000 > 0.01` → `has_error = True` ❌

**Правильная логика (из Domain модели):**
```python
# src/domain/models/deal.py:855
@computed_field
def has_totals_error(self) -> Optional[bool]:
    # Если все totals = NULL, возвращаем None (нет данных)
    if (self.total_revenue is None and 
        self.total_margin is None and 
        self.total_cost is None):
        return None
    
    # Если total = None, это не ошибка
    def _mismatch(src_money: Money | None, calc_amount: Decimal) -> bool:
        if src_money is None:
            return False  # ✅ NULL не считается ошибкой
        return abs(src_money.amount - calc_amount) > THRESHOLD_DECIMAL
    
    return (_mismatch(self.total_revenue, calc_rev) or
            _mismatch(self.total_margin, calc_mar) or
            _mismatch(self.total_cost, calc_cost))
```

**Анализ:**
- Domain модель содержит **правильную** бизнес-логику
- Infrastructure дублирует эту логику, но **неправильно**
- Это классический пример нарушения DRY и потери синхронности

**Приоритет исправления:** КРИТИЧЕСКИЙ (30 минут работы)

**Риски исправления:** НИЗКИЕ - логика становится идентичной Domain

### 3.3 BUG-003: deal_key mismatch [ТРЕБУЕТ ПРОВЕРКИ]

**Файл:** `src/infrastructure/database/repositories.py:244-261`

**Потенциальная проблема:**
```python
async def _read_model_to_domain(self, model: ReadModelDeal) -> Deal:
    builder = DealBuilder(period=period)
    builder.invoice_number = model.invoice_number or None  # ⚠️ None vs ""?
    builder.invoice_date = model.invoice_date or None      # ⚠️ None vs ""?
    builder.seller = model.seller or "UNKNOWN"             # ⚠️ Fallback!
    deal = builder.build()  # deal_key вычисляется заново
```

**Из domain/models/deal.py:702:**
```python
@computed_field
def deal_key(self) -> str:
    num = (self.invoice_number or "").strip().lower()
    date = (self.invoice_date or "").strip().lower()
    seller = (self.seller or "").strip().lower()
    period_str = str(self.period).lower()
    return f"{num}|{date}|{seller}|{period_str}"
```

**Анализ:**

Если:
- В Excel: `invoice_number = ""` (пустая строка)
- В БД сохранено: `invoice_number = NULL`
- При загрузке: `or None` не влияет, т.к. `("" or "")` → `""`
- При вычислении deal_key: `("" or "").strip().lower()` → `""`

**Вывод:** Логика **скорее всего правильная**, но требует unit-теста:

```python
def test_deal_key_consistency():
    # Excel: пустая строка
    deal1 = Deal(invoice_number="", ...)
    
    # БД: NULL
    deal2 = Deal(invoice_number=None, ...)
    
    assert deal1.deal_key == deal2.deal_key  # Должны совпадать
```

**Приоритет проверки:** ВЫСОКИЙ (1 час работы)

---

## 4. АНАЛИЗ РИСКОВ И ПРИОРИТИЗАЦИЯ

### 4.1 Матрица рисков

| Риск | Вероятность | Влияние | Приоритет |
|------|-------------|---------|-----------|
| BUG-001: Audit не работает | 100% | Средний | P1 (немедленно) |
| BUG-002: has_totals_error | 100% | Высокий | P1 (немедленно) |
| BUG-003: deal_key mismatch | 30% | Критичный | P2 (срочно) |
| Отсутствие тестов | 100% | Высокий | P2 (срочно) |
| Deferred events накопление | 20% | Средний | P3 (важно) |
| Транзакции в циклах | 50% | Средний | P3 (важно) |

### 4.2 План исправления (приоритеты)

#### Этап 1: Критические баги (1 день)
1. **FIX-001:** Удалить `return` на строке 1225 ✅ (5 мин)
2. **FIX-002:** Исправить логику `has_totals_error` ✅ (30 мин)
3. **TEST-001:** Unit-тест для deal_key consistency ✅ (1 час)
4. **INT-TEST-001:** Интеграционный тест double-sync ✅ (2 часа)

#### Этап 2: Архитектурные улучшения (3 дня)
5. **REFACTOR-001:** Вынести commit из `_upsert_position` (1 час)
6. **REFACTOR-002:** Разделить ReadModelBuilder на компоненты (1 день)
7. **FEATURE-001:** Механизм retry для deferred events (1 день)
8. **TEST-002:** Покрытие тестами change_detector (1 день)

#### Этап 3: Мониторинг и наблюдаемость (2 дня)
9. **MONITOR-001:** Метрики для deferred queue size
10. **MONITOR-002:** Алерты на длительность синхронизации
11. **LOGGING-001:** Детальное логирование deal_key на всех этапах

---

## 5. СПЕЦИФИЧЕСКИЕ ЗАМЕЧАНИЯ

### 5.1 Change Detector

**Проверено:** `src/application/change_detector/detector.py`

**Оценка:** ✅ АРХИТЕКТУРНО ПРАВИЛЬНО

Логика детекции изменений реализована **корректно**:
- Hash-based comparison для производительности
- Fallback на detailed comparison при расхождении
- Использование deal_key как бизнес-ключа
- Правильная категоризация INSERT/UPDATE/DELETE

**Единственное замечание:**
```python
# Строка 139
return []  # При ошибке возвращает пустой список
```

Это **маскирует** проблемы. Лучше:
```python
logger.error(f"Failed to get database deals: {e}")
raise  # Пусть orchestrator обработает
```

### 5.2 Excel Parser

**Не анализировалось детально**, но из плана видно:

**Риск R1.1:** Потеря точности float → Decimal

Проверьте:
```python
# Где происходит парсинг из Excel
value = cell.value  # float
decimal_value = Decimal(str(value))  # ✅ Правильно через str
# НЕ: Decimal(value)  # ❌ Потеря точности
```

**Риск R1.4:** xlcalculator не справляется со сложными формулами

Из `EXCEL_FORMULA_CALCULATION.md` видно, что используется CACHE_ONLY режим. Это **правильное** решение для production.

### 5.3 Sync Orchestrator

**Проверено:** `src/application/sync_orchestrator/orchestrator.py`

**Оценка:** ✅ КОРРЕКТНО, но есть TODO

```python
# TODO: Implement proper rollback on failure
if config.rollback_on_failure:
    logger.warning("Rollback on failure not yet implemented")
```

**Это критическая функциональность!** Без rollback при падении в середине синхронизации получаем:
- Часть событий в event_store
- Часть read models обновлена
- Inconsistent state

**Рекомендация:** Использовать database transactions:
```python
async with session.begin():
    # Вся синхронизация в одной транзакции
    if error:
        raise  # Автоматический rollback
```

---

## 6. ОЦЕНКА ПЛАНА АНАЛИЗА

### 6.1 Сильные стороны плана

1. **Структурированность:** Четкое разделение на блоки, приложения, чеклисты
2. **Детальность:** Каждый компонент описан с критериями корректности
3. **Практичность:** Quick fixes + investigation plan
4. **Контрольные тесты:** SQL запросы для проверки исправлений
5. **Приоритизация:** Критические баги выделены

### 6.2 Что можно улучшить

1. **Недостаточно внимания к тестированию:**
   - План не включает создание unit-тестов
   - Нет проверки покрытия кода
   - Контрольные тесты только SQL

2. **Не учтена наблюдаемость:**
   - Нет метрик для мониторинга
   - Не проверено логирование
   - Нет трейсинга запросов

3. **Отсутствует анализ производительности:**
   - Нет нагрузочного тестирования
   - Не проверены индексы БД
   - Не оценен worst-case сценарий

4. **Нет анализа зависимостей:**
   - Какие версии библиотек используются?
   - Есть ли известные уязвимости?
   - Совместимость версий

---

## 7. ИТОГОВЫЕ РЕКОМЕНДАЦИИ

### 7.1 Немедленные действия (P1)

1. ✅ Исправить BUG-001 (audit)
2. ✅ Исправить BUG-002 (has_totals_error)
3. ✅ Написать тест на deal_key consistency
4. ✅ Протестировать двойную синхронизацию

### 7.2 Краткосрочные (P2) - 1 неделя

1. Добавить unit-тесты для:
   - Change detector
   - Read model builder
   - Domain models (has_totals_error, deal_key)

2. Реализовать rollback_on_failure

3. Вынести commit из циклов

4. Добавить мониторинг deferred queue

### 7.3 Среднесрочные (P3) - 1 месяц

1. Рефакторинг ReadModelBuilder на компоненты

2. Dead letter queue для deferred events

3. Нагрузочное тестирование

4. CI/CD с автоматическими тестами

### 7.4 Архитектурные решения

**Что оставить как есть:**
- Event Sourcing паттерн ✅
- CQRS разделение ✅
- Hash-based change detection ✅
- DDD структура ✅

**Что изменить:**
- Транзакционная целостность ❌
- Разделение ответственностей в workers ❌
- Дублирование бизнес-логики между Domain и Infrastructure ❌

---

## 8. ЗАКЛЮЧЕНИЕ

### 8.1 Общая оценка проекта

**Оценка архитектуры: 8/10**

Проект демонстрирует **высокий уровень архитектурной зрелости**:
- Правильное применение сложных паттернов
- Продуманная оптимизация
- Четкая структура кода

**Критические недостатки:**
- Отсутствие тестов
- Дублирование логики
- Транзакционная целостность

### 8.2 Оценка плана анализа

**Оценка плана: 9/10**

План составлен **профессионально** и **детально**. Автор:
- Нашел реальные баги
- Правильно расставил приоритеты
- Предложил конкретные исправления

**Рекомендация:** Следовать плану, дополнив:
- Unit-тесты
- Мониторинг
- Нагрузочное тестирование

### 8.3 Риски

**Основной риск:** Изменения в production без тестов могут внести новые баги.

**Митигация:**
1. Создать тесты **до** исправлений
2. Тестировать на копии production БД
3. Постепенный rollout (canary deployment)

---

## 9. ПРИЛОЖЕНИЯ

### Приложение A: Предложенные тесты

```python
# tests/unit/test_deal_key_consistency.py

import pytest
from domain.models import Deal
from domain.builders import DealBuilder
from domain.value_objects import Period

def test_deal_key_with_empty_vs_none():
    """Проверка: пустая строка и None дают одинаковый deal_key."""
    period = Period(month="1", year="2025", full_name="Январь 2025")
    
    # Deal с пустыми строками
    deal1 = Deal(
        client_name="Test",
        invoice_info="Info",
        invoice_number="",
        invoice_date="",
        seller="Seller",
        period=period,
        period_month="1",
        period_year="2025"
    )
    
    # Deal с None
    deal2 = Deal(
        client_name="Test",
        invoice_info="Info",
        invoice_number=None,
        invoice_date=None,
        seller="Seller",
        period=period,
        period_month="1",
        period_year="2025"
    )
    
    assert deal1.deal_key == deal2.deal_key

def test_has_totals_error_with_all_nulls():
    """Проверка: все totals = NULL → has_totals_error = None."""
    period = Period(month="1", year="2025", full_name="Январь 2025")
    
    deal = Deal(
        client_name="Test",
        invoice_info="Info",
        seller="Seller",
        period=period,
        period_month="1",
        period_year="2025",
        total_revenue=None,
        total_margin=None,
        total_cost=None
    )
    
    assert deal.has_totals_error is None

# tests/integration/test_double_sync.py

import pytest
from pathlib import Path

@pytest.mark.asyncio
async def test_second_sync_creates_no_events(orchestrator, test_excel_file, db_session):
    """Проверка: повторная синхронизация того же файла не создает новых событий."""
    
    # Первая синхронизация
    config = SyncConfiguration(sync_type=SyncType.FULL)
    result1 = await orchestrator.execute_sync(test_excel_file, config)
    
    # Подсчет событий
    events_count_1 = await db_session.execute(
        "SELECT COUNT(*) FROM event_store"
    )
    count_1 = events_count_1.scalar()
    
    # Вторая синхронизация
    result2 = await orchestrator.execute_sync(test_excel_file, config)
    
    # Подсчет событий после второй синхронизации
    events_count_2 = await db_session.execute(
        "SELECT COUNT(*) FROM event_store"
    )
    count_2 = events_count_2.scalar()
    
    # Не должно быть новых событий (все detected как unchanged)
    assert count_2 == count_1, "Повторная синхронизация создала новые события!"
    assert result2.change_detection_result.total_changes == 0
```

### Приложение B: Предложенные метрики

```python
# src/infrastructure/monitoring/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Счетчики событий
events_created = Counter(
    'sync_events_created_total',
    'Total number of events created',
    ['event_type']
)

# Длительность операций
sync_duration = Histogram(
    'sync_duration_seconds',
    'Duration of sync operations',
    ['sync_type']
)

# Размер deferred queue
deferred_queue_size = Gauge(
    'deferred_queue_size',
    'Number of events in deferred queue'
)

# Ошибки
sync_errors = Counter(
    'sync_errors_total',
    'Total number of sync errors',
    ['error_type']
)
```

---

**Документ подготовлен:** 29 ноября 2025  
**Версия:** 1.0  
**Статус:** Готов к обсуждению

