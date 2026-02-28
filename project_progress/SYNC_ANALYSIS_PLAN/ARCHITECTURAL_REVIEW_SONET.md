# АРХИТЕКТУРНОЕ РЕВЬЮ ПЛАНА АНАЛИЗА СИНХРОНИЗАЦИИ

**Дата:** 29 ноября 2025  
**Ревьюер:** Системный архитектор  
**Статус:** Готов к обсуждению  
**Версия:** 1.0

---

## РЕЗЮМЕ

План анализа выполнен на **высоком профессиональном уровне**. Автор демонстрирует глубокое понимание архитектуры Event Sourcing + CQRS, корректно идентифицировал критические баги и предложил адекватные пути исправления.

**Оценка плана: 8.5/10**

### Сильные стороны плана
- Структурированный подход к анализу (от общего к частному)
- Корректная идентификация 3 критических багов с доказательствами
- Понимание Domain-Driven Design и Event Sourcing паттернов
- Детальные чеклисты для проверки каждого компонента
- Приоритизация задач по важности

### Области для улучшения
- Недостаточно внимания к производительности и масштабируемости
- Отсутствует анализ транзакционной консистентности
- Не рассмотрены сценарии сбоев и recovery
- Слабо проработана проблема BUG-003 (требует глубокой диагностики)

---

## ЧАСТЬ 1: АНАЛИЗ НАЙДЕННЫХ БАГОВ

### BUG-001: `_create_audit_entry` никогда не создает записи [КРИТИЧЕСКИЙ] ✅

**Оценка находки:** ОТЛИЧНО

**Анализ:**
```python
# Строка 1225 в read_model_builder.py
async def _create_audit_entry(...):
    try:
        if additional_data:
            logger.debug(...)
        else:
            logger.debug(...)
        return  # <-- БАГ подтвержден: код ниже недостижим
        
        audit_entry = ReadModelAudit(...)  # Dead code
        self.session.add(audit_entry)
```

**Вердикт:** Баг подтвержден. Код аудита действительно недостижим из-за раннего `return`.

**Критические замечания:**
1. **Это не баг, а FEATURE TOGGLE в режиме "выключен"**  
   Судя по коду, разработчик намеренно отключил audit через return, возможно из-за проблем с производительностью.
   
2. **Простое удаление return может вызвать новые проблемы:**
   - Производительность: создание audit для КАЖДОГО изменения (сотни/тысячи записей)
   - Транзакции: нет коммита после `session.add()`
   - Дублирование: при повторной обработке событий

**Рекомендация:**
```python
# Вариант A: Feature flag через конфигурацию
async def _create_audit_entry(...):
    if not self.config.enable_audit_logging:
        logger.debug(f"Audit disabled: {entity_type} {change_type}")
        return
    
    # ... код создания audit
    
# Вариант B: Асинхронная запись через очередь (не блокирует синхронизацию)
async def _create_audit_entry(...):
    audit_data = {...}
    await self.audit_queue.enqueue(audit_data)  # Non-blocking
```

**Приоритет исправления:** Средний (не влияет на корректность данных, только на трассируемость)

---

### BUG-002: `has_totals_error` некорректно обрабатывает NULL [КРИТИЧЕСКИЙ] ✅

**Оценка находки:** ОТЛИЧНО

**Анализ:**
```python
# Текущая логика (НЕПРАВИЛЬНО)
def _delta(src: Decimal | None, calc: Decimal) -> Decimal:
    return abs((src or Decimal("0")) - calc)  # NULL трактуется как 0!

has_error = any(
    _delta(val, calc) > Decimal("0.01")
    for val, calc in ((src_rev, rev), (src_mar, mar), (src_cost, cost))
)
```

**Пример ошибочного поведения:**
- Excel: `total_revenue = NULL` (режим no_cash)
- Calculated: `calc_revenue = 1000.00`
- `_delta(NULL, 1000) = abs(0 - 1000) = 1000 > 0.01` → **has_error = True** ❌

**Правильная бизнес-логика (из Domain модели):**
```python
# Deal.has_totals_error - ПРАВИЛЬНО
if self.total_revenue is None and self.total_margin is None and self.total_cost is None:
    return None  # Нет данных для сравнения (не ошибка!)
```

**Вердикт:** Баг подтвержден. Это **КРИТИЧЕСКИЙ баг бизнес-логики**, влияющий на корректность флага has_totals_error.

**Критические замечания:**
1. **Нарушение Domain Invariant**  
   Infrastructure слой (read_model_builder) реализует логику иначе, чем Domain модель. Это нарушение DDD принципа: business logic должна быть в Domain.

2. **Предложенное исправление корректно, но неполно:**
   ```python
   # План предлагает:
   def _has_mismatch(src: Decimal | None, calc: Decimal) -> bool:
       if src is None:
           return False  # NULL = нет ошибки
       return abs(src - calc) > Decimal("0.01")
   
   # Но что если src=100, calc=100.005? Это ошибка?
   # THRESHOLD_DECIMAL = 0.01 может быть слишком строгим для некоторых валют
   ```

3. **Нет обработки edge case: что если calc = NULL?**  
   Если items пустые, calc_revenue может быть NULL или 0. Нужна проверка.

**Рекомендация:**
```python
async def _recalculate_totals(self, deal_id: uuid.UUID) -> None:
    # ... получение данных ...
    
    # CRITICAL: Если нет позиций, calc_* должны быть NULL, а не 0
    if items_cnt == 0:
        has_error = None  # Нет данных для сравнения
    else:
        # Все declared totals = NULL → режим no_cash
        all_declared_null = (src_rev is None and src_mar is None and src_cost is None)
        
        if all_declared_null:
            has_error = None
        else:
            # Сравнение только там, где declared не NULL
            def _has_mismatch(declared: Decimal | None, calculated: Decimal) -> bool:
                if declared is None:
                    return False  # NULL declared = нет требования к сравнению
                return abs(declared - calculated) > Decimal("0.01")
            
            has_error = any(
                _has_mismatch(val, calc)
                for val, calc in ((src_rev, rev), (src_mar, mar), (src_cost, cost))
            )
    
    # Обновление с явным указанием NULL
    await self.session.execute(
        update(ReadModelDeal)
        .where(ReadModelDeal.id == deal_id)
        .values(
            items_count=items_cnt,
            calc_revenue_amount=rev if items_cnt > 0 else None,
            calc_margin_amount=mar if items_cnt > 0 else None,
            calc_cost_amount=cost if items_cnt > 0 else None,
            has_totals_error=has_error,
        )
    )
```

**Приоритет исправления:** КРИТИЧЕСКИЙ (влияет на корректность бизнес-логики)

---

### BUG-003: Потенциальная проблема с deal_key при загрузке из БД [СРЕДНИЙ] ⚠️

**Оценка находки:** Хорошо замечено, но **требует глубокой диагностики**

**Анализ из repositories.py (строки 244-261):**
```python
def _read_model_to_domain(self, model: ReadModelDeal) -> Deal:
    period = Period(month=model.period_month, year=model.period_year, ...)
    
    builder = DealBuilder(period=period)
    builder.client_name = model.client_name
    builder.invoice_number = model.invoice_number or None  # None vs ""?
    builder.invoice_date = model.invoice_date or None      # None vs ""?
    builder.seller = model.seller or "UNKNOWN"             # Fallback!
    
    deal = builder.build()  # deal_key вычисляется заново
    # ПРОБЛЕМА: deal.deal_key может не совпасть с model.deal_key
```

**Вердикт:** Это **ПОТЕНЦИАЛЬНЫЙ** баг, требующий проверки. План правильно идентифицировал риск, но не предоставил доказательств.

**Критические замечания:**

1. **Глубинная проблема: Нарушение идемпотентности**
   
   Рассмотрим сценарий:
   ```
   Excel parse → Deal(invoice_number="123", seller="John Smith")
                 deal_key = "123|2025-01-01|John Smith|2025-01"
                 
   Save to DB → ReadModelDeal(invoice_number="123", seller="John Smith", deal_key="...")
   
   Load from DB → builder.invoice_number = "123" or None  # "123"
                  builder.seller = "John Smith" or "UNKNOWN"  # "John Smith"
                  deal = builder.build()
                  deal.deal_key = "123|2025-01-01|John Smith|2025-01"  # OK
   
   BUT if Excel has seller=""
   Parse → Deal(seller="")
           deal_key = "|2025-01-01||2025-01"  # Пустой seller
   
   Save to DB → ReadModelDeal(seller="")
   
   Load from DB → builder.seller = "" or "UNKNOWN"  # "UNKNOWN" !!!
                  deal.deal_key = "123|2025-01-01|UNKNOWN|2025-01"  # MISMATCH!
   ```

2. **Риск нормализации строк:**
   ```python
   # Excel parser может делать .strip()
   seller = "  John Smith  ".strip()  # "John Smith"
   
   # Но при загрузке из БД:
   builder.seller = model.seller or "UNKNOWN"  # Нет .strip()!
   # Если в БД хранится "  John Smith  ", deal_key не совпадет
   ```

3. **Детерминированный ID (uuid5) тоже пострадает:**
   ```python
   # Deal.id вычисляется через uuid5(namespace, deal_key)
   # Если deal_key меняется при загрузке → ID меняется → данные потеряны!
   ```

**Рекомендация:**

**Вариант A: Использовать сохраненный deal_key (НЕ пересчитывать)**
```python
def _read_model_to_domain(self, model: ReadModelDeal) -> Deal:
    # ... построение через builder ...
    deal = builder.build()
    
    # CRITICAL: Переопределить deal_key из БД (не пересчитывать!)
    deal._deal_key = model.deal_key  # Private field override
    deal.set_id(model.id)  # Использовать сохраненный ID
    
    return deal
```

**Вариант B: Добавить валидацию после загрузки**
```python
def _read_model_to_domain(self, model: ReadModelDeal) -> Deal:
    deal = builder.build()
    
    # Валидация: проверить совпадение
    if deal.deal_key != model.deal_key:
        logger.error(
            f"deal_key mismatch! Calculated: {deal.deal_key}, Stored: {model.deal_key}"
        )
        # FALLBACK: использовать сохраненный
        deal._deal_key = model.deal_key
    
    return deal
```

**Вариант C (ЛУЧШИЙ): Хранить компоненты deal_key, а не вычислять**
```python
# В Domain модели Deal сделать deal_key иммутабельным при создании
@computed_field
def deal_key(self) -> str:
    if self._stored_deal_key:  # Если загружено из БД
        return self._stored_deal_key
    # Иначе вычислить
    return self._build_deal_key()
```

**Диагностический скрипт (из плана):**
```python
# ДОБАВИТЬ в change_detector для диагностики
async def _get_database_deals(self, excel_deals, sync_period_months):
    db_deals = await self.deal_repository.find_by_period(...)
    
    # DEBUG: Сравнить deal_key из БД с пересчитанным
    for db_deal in db_deals:
        recalculated_key = db_deal._build_deal_key()  # Если есть такой метод
        if db_deal.deal_key != recalculated_key:
            logger.warning(
                f"deal_key mismatch: stored={db_deal.deal_key}, "
                f"recalculated={recalculated_key}"
            )
```

**Приоритет исправления:** ВЫСОКИЙ (потенциально влияет на корректность change detection)

---

## ЧАСТЬ 2: АНАЛИЗ АРХИТЕКТУРЫ

### 2.1 Соответствие DDD принципам

**Оценка: 7.5/10**

#### ✅ Сильные стороны:

1. **Четкое разделение слоев:**
   ```
   Domain (models, value_objects, interfaces)
   Application (use cases: parser, change_detector, orchestrator)
   Infrastructure (БД, workers, mappers)
   ```

2. **Aggregates и Entities корректно спроектированы:**
   - Deal = Aggregate Root
   - DealItem = Entity (дочерняя сущность)
   - Invariants обеспечиваются в Domain

3. **Value Objects с правильной семантикой:**
   - Money, Money5 с точностью
   - Period (иммутабельный)
   - HashKey (для change detection)
   - Status (enum для is_shipped, is_paid)

4. **Repository Pattern:**
   - Абстрактные интерфейсы в Domain
   - Реализация в Infrastructure
   - Скрывает детали персистенции

#### ❌ Слабые стороны:

1. **Нарушение Domain Logic в Infrastructure**
   
   **Проблема:** `_recalculate_totals()` в `ReadModelBuilder` дублирует бизнес-логику из `Deal.has_totals_error`.
   
   **Почему это плохо:**
   - Бизнес-логика размазана по 2 местам
   - Infrastructure знает о правилах сравнения totals (нарушение DDD)
   - При изменении логики нужно обновлять 2 места
   
   **Решение:**
   ```python
   # Domain: Deal должна предоставлять метод для расчета
   class Deal:
       def calculate_totals_from_items(self) -> dict:
           """Calculate and return totals dict."""
           return {
               "calc_revenue": sum(item.revenue for item in self.items),
               "calc_margin": sum(item.margin for item in self.items),
               "calc_cost": sum(item.cost for item in self.items),
               "has_error": self._check_totals_error(...),
           }
   
   # Infrastructure: использовать Domain метод
   async def _recalculate_totals(self, deal_id: UUID):
       deal = await self._load_deal(deal_id)  # Загрузить Domain модель
       totals = deal.calculate_totals_from_items()
       
       # Просто сохранить результат
       await self.session.execute(
           update(ReadModelDeal).values(**totals)
       )
   ```

2. **Отсутствие Domain Services для сложной логики**
   
   **Проблема:** Change Detection логика размещена в Application слое, но содержит бизнес-правила.
   
   **Решение:**
   ```python
   # Domain/services/change_detection_service.py
   class DomainChangeDetectionService:
       """Domain service для определения изменений между Deal объектами."""
       
       def compare_deals(self, deal1: Deal, deal2: Deal) -> ChangeResult:
           """Compare two deals and return detailed changes."""
           # Бизнес-логика сравнения
   
   # Application использует Domain service
   class ChangeDetectorService:
       def __init__(self, domain_service: DomainChangeDetectionService):
           self.domain_service = domain_service
   ```

3. **Builder Pattern не полностью реализован**
   
   **Проблема:** `DealBuilder` не валидирует инварианты до вызова `build()`.
   
   ```python
   # Текущий код
   builder = DealBuilder(period=period)
   builder.seller = ""  # Пустой seller! Но build() не проверяет
   deal = builder.build()  # Deal создается с невалидными данными
   ```
   
   **Решение:**
   ```python
   class DealBuilder:
       def build(self) -> Deal:
           # Валидация перед созданием
           if not self.seller or self.seller.strip() == "":
               raise ValueError("Seller cannot be empty")
           
           if not self.invoice_number and not self.invoice_date:
               raise ValueError("Either invoice_number or invoice_date required")
           
           return Deal(...)
   ```

---

### 2.2 Event Sourcing + CQRS реализация

**Оценка: 8/10**

#### ✅ Сильные стороны:

1. **Правильная структура событий:**
   ```
   event_store:
       event_id (PK)
       aggregate_id (UUID детерминированный)
       sequence_number (порядок в рамках aggregate)
       event_type (DealCreated, DealItemAdded, ...)
       event_data (JSONB payload)
       processed_at (маркер обработки)
   ```

2. **Разделение Write и Read моделей:**
   - Write: события в event_store (источник истины)
   - Read: денормализованные таблицы (read_deals, read_positions)

3. **Идемпотентность событий:**
   - sequence_number обеспечивает порядок
   - processed_at предотвращает повторную обработку

#### ❌ Слабые стороны:

1. **Нет обработки Race Conditions**
   
   **Проблема:** Параллельная запись событий для одного aggregate может нарушить sequence_number.
   
   ```python
   # Thread 1: INSERT event (aggregate_id=A, sequence=5)
   # Thread 2: INSERT event (aggregate_id=A, sequence=5)  # Конфликт!
   ```
   
   **Решение:**
   ```python
   # Option A: Optimistic locking
   CREATE UNIQUE INDEX idx_aggregate_sequence 
       ON event_store(aggregate_id, sequence_number);
   
   # Option B: Pessimistic locking
   async def append_events(self, events):
       async with self.lock_manager.acquire(aggregate_id):
           max_seq = await self._get_max_sequence(aggregate_id)
           for event in events:
               event.sequence_number = max_seq + 1
               await self._insert_event(event)
               max_seq += 1
   ```

2. **Нет Snapshot механизма**
   
   **Проблема:** Для восстановления состояния Deal нужно проигрывать ВСЕ события с начала времен.
   
   Если у Deal 10,000 событий → медленная загрузка.
   
   **Решение:**
   ```python
   # Snapshots таблица
   CREATE TABLE event_snapshots (
       aggregate_id UUID PRIMARY KEY,
       sequence_number INT,  -- Номер последнего события в snapshot
       snapshot_data JSONB,
       created_at TIMESTAMP
   );
   
   # Восстановление
   async def load_deal(self, deal_id: UUID) -> Deal:
       snapshot = await self._get_latest_snapshot(deal_id)
       events = await self.event_store.get_events(
           aggregate_id=deal_id,
           from_sequence=snapshot.sequence_number + 1
       )
       
       deal = Deal.from_snapshot(snapshot.data)
       for event in events:
           deal.apply_event(event)
       
       return deal
   ```

3. **Отсутствие Saga для сложных процессов**
   
   **Проблема:** Если синхронизация падает посередине, как откатить частичные изменения?
   
   **Текущий код:**
   ```python
   # orchestrator.py
   async def execute_sync(...):
       # 1. Parse Excel
       # 2. Detect changes
       # 3. Create events
       # 4. Update read models
       # Если падает на шаге 3 → read models не обновлены, но события частично записаны
   ```
   
   **Решение:**
   ```python
   # Saga pattern для транзакционности
   class SyncSaga:
       async def execute(self):
           try:
               # Step 1
               await self.parse_excel()
               await self.save_checkpoint("parsed")
               
               # Step 2
               await self.detect_changes()
               await self.save_checkpoint("detected")
               
               # Step 3
               await self.create_events()
               await self.save_checkpoint("events_created")
               
               # Step 4
               await self.update_read_models()
               await self.complete_saga()
               
           except Exception as e:
               # Компенсирующие транзакции
               await self.rollback_from_last_checkpoint()
   ```

---

### 2.3 Производительность и масштабируемость

**Оценка: 6/10** (План НЕ рассматривает эту тему)

#### Проблемы, не упомянутые в плане:

1. **N+1 Query Problem в ReadModelBuilder**
   
   ```python
   # Текущий код (МЕДЛЕННО)
   for event in events:
       if event.type == "DealItemAdded":
           deal = await self._get_deal_context(event.aggregate_id)  # SELECT каждый раз!
           await self._upsert_position(...)
           await self._recalculate_totals(deal.id)  # SELECT + UPDATE
   
   # Если 1000 items → 1000 * 3 = 3000 запросов!
   ```
   
   **Решение:**
   ```python
   # Batch processing
   async def process_events_batch(self, events):
       # Group by aggregate_id
       events_by_aggregate = defaultdict(list)
       for event in events:
           events_by_aggregate[event.aggregate_id].append(event)
       
       # Load all deals once
       deal_ids = list(events_by_aggregate.keys())
       deals = await self._load_deals_batch(deal_ids)
       
       # Process in batch
       for aggregate_id, deal_events in events_by_aggregate.items():
           deal = deals[aggregate_id]
           for event in deal_events:
               await self._process_event(event, deal)
           
           # Recalculate once per deal
           await self._recalculate_totals(deal.id)
   ```

2. **Транзакции внутри цикла**
   
   ```python
   # SimplePositionSync._upsert_position()
   async def _upsert_position(self, ...):
       # ... INSERT/UPDATE ...
       await self.session.commit()  # COMMIT внутри цикла!
   
   # Если 1000 позиций → 1000 коммитов → медленно
   ```
   
   **Решение:**
   ```python
   # Batch insert с RETURNING для проверки конфликтов
   async def _upsert_positions_batch(self, positions: list):
       stmt = insert(ReadModelPosition).values([
           p.dict() for p in positions
       ]).on_conflict_do_update(
           index_elements=['hash_key'],
           set_={'updated_at': datetime.now(), ...}
       )
       await self.session.execute(stmt)
       # Один commit вне цикла
   ```

3. **Отсутствие индексов для change detection**
   
   План не проверяет наличие индексов:
   ```sql
   -- Для быстрого find_by_period
   CREATE INDEX idx_read_deals_period ON read_deals(period_year, period_month);
   
   -- Для быстрого поиска по hash_key
   CREATE INDEX idx_read_deals_hash ON read_deals(hash_deal_key);
   CREATE INDEX idx_read_positions_hash ON read_positions(hash_key);
   
   -- Для быстрой обработки событий
   CREATE INDEX idx_event_store_processed ON event_store(processed_at)
       WHERE processed_at IS NULL;
   ```

---

## ЧАСТЬ 3: КРИТИЧЕСКИЙ АНАЛИЗ ПЛАНА

### 3.1 Что План НЕ покрывает (но должен)

1. **Транзакционная консистентность**
   
   **Вопрос:** Что если read model обновился, но processed_at не установился из-за сбоя?
   
   ```python
   # Текущий код
   async def _handle_deal_event(self, event):
       await self._upsert_deal(...)  # Изменяет БД
       await self.session.commit()
       
       # Сбой здесь → deal обновлен, но event не помечен processed!
       await self._mark_processed(event.id)
   ```
   
   **Последствия:**
   - При следующем запуске событие обработается повторно
   - Дублирование данных в read models
   
   **Решение:**
   ```python
   async def _handle_deal_event(self, event):
       async with self.session.begin():  # Одна транзакция
           await self._upsert_deal(...)
           await self._mark_processed(event.id)
       # commit() автоматически, rollback при ошибке
   ```

2. **Обработка параллельных синхронизаций**
   
   План не рассматривает сценарий:
   ```
   User 1: запускает sync для January.xlsx
   User 2: запускает sync для February.xlsx (параллельно)
   
   Вопрос: что если оба пытаются обновить одну и ту же сделку?
   ```
   
   **Решение:**
   ```python
   # Distributed lock через Redis
   async def execute_sync(self, file_path, config):
       async with self.lock_manager.acquire(f"sync:{file_path}"):
           # Только одна синхронизация файла одновременно
           await self._do_sync()
   ```

3. **Мониторинг и алертинг**
   
   План фокусируется на багах, но не на наблюдаемости:
   - Нет метрик Prometheus (latency, throughput, error rate)
   - Нет structured logging для ELK/Loki
   - Нет health checks для API
   
   **Рекомендация:**
   ```python
   # Metrics
   sync_duration = Histogram('sync_duration_seconds', 'Sync duration')
   event_processing_rate = Counter('events_processed_total', 'Events processed')
   error_rate = Counter('sync_errors_total', 'Sync errors', ['error_type'])
   
   # Logging
   logger.info("sync_started", extra={
       "session_id": session_id,
       "file_path": file_path,
       "file_size": file_size,
   })
   ```

4. **Disaster Recovery**
   
   Что если:
   - event_store таблица повреждена?
   - read_models рассинхронизировались с event_store?
   
   **Решение:**
   ```python
   # Rebuild read models from scratch
   async def rebuild_read_models(self):
       # 1. Truncate read models
       await self.session.execute(delete(ReadModelDeal))
       await self.session.execute(delete(ReadModelPosition))
       
       # 2. Reset processed_at
       await self.session.execute(
           update(EventStore).values(processed_at=None)
       )
       
       # 3. Replay all events
       await self.read_model_builder.process_latest_events(limit=999999)
   ```

---

### 3.2 Порядок выполнения анализа (Из плана)

| Этап | Оценка | Комментарий |
|------|--------|-------------|
| 1. Архитектурный обзор | ✅ Хорошо | Структурировано, покрывает основные компоненты |
| 2. Change Detector | ✅ Отлично | BUG-003 правильно идентифицирован |
| 3. Read Model Builder | ✅ Отлично | BUG-001, BUG-002 найдены с доказательствами |
| 4. Excel Parser | ⚠️ Средне | Не рассмотрены edge cases (пустые листы, формулы ошибок) |
| 5. Domain Models | ✅ Хорошо | Понимание computed_field и hash_key |
| 6. Sync Orchestrator | ⚠️ Средне | Не рассмотрен rollback механизм |
| 7. Event Store | ⚠️ Слабо | Не рассмотрены race conditions, snapshots |
| 8. Simple Position Sync | ⚠️ Слабо | Не замечена проблема commit() в цикле |

**Общая оценка порядка: 7/10**

---

## ЧАСТЬ 4: РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ ПЛАНА

### 4.1 Добавить в план

1. **Раздел "Транзакционная модель"**
   - Границы транзакций для каждого компонента
   - Стратегия обработки partial failures
   - Idempotency guarantees

2. **Раздел "Производительность"**
   - Benchmarks для каждого блока (парсинг, change detection, event processing)
   - Профилирование узких мест
   - Планы оптимизации

3. **Раздел "Тестирование"**
   - Unit tests для Domain logic
   - Integration tests для Repository
   - E2E tests для полного sync flow
   - Property-based testing для hash_key

4. **Раздел "Deployment и Rollback"**
   - Стратегия миграции БД (Alembic)
   - Backward compatibility для событий
   - Blue-Green deployment

---

### 4.2 Изменить приоритеты

План предлагает:
```
1. FIX-001: Audit (5 мин)
2. FIX-002: has_totals_error (30 мин)
3. INV-001: event_store (1-2 ч)
```

**Мое мнение:**
```
1. FIX-002: has_totals_error (КРИТИЧЕСКИЙ бизнес-баг) → 1 час
2. INV-001: event_store + BUG-003 (причина всех проблем) → 3-4 часа
3. FIX-001: Audit (не влияет на корректность) → 1 час + тесты производительности
```

**Обоснование:**
- has_totals_error влияет на корректность отчетов → **ПРИОРИТЕТ #1**
- event_store проблема (все данные как INSERT) → **ПРИОРИТЕТ #2**
- Audit нужен для compliance, но не влияет на функциональность → **ПРИОРИТЕТ #3**

---

## ЧАСТЬ 5: ПЛАН ДЕЙСТВИЙ (ДОРАБОТАННЫЙ)

### Этап 1: Диагностика BUG-003 (КРИТИЧНО)

**Цель:** Понять, почему все данные попадают в event_store как INSERT.

**Гипотеза 1:** `find_by_period` возвращает пустой список
```python
# Проверка
async def test_find_by_period():
    deals = await repository.find_by_period(month="01", year="2025")
    print(f"Found {len(deals)} deals")
    
    if len(deals) == 0:
        # Проверить данные в read_deals
        result = await session.execute(
            select(ReadModelDeal).where(
                ReadModelDeal.period_year == "2025",
                ReadModelDeal.period_month == "01"
            )
        )
        raw_deals = result.scalars().all()
        print(f"Raw query found {len(raw_deals)} deals")
        
        if len(raw_deals) > 0:
            # Проблема в find_by_period реализации
            print("BUG: find_by_period не возвращает данные!")
        else:
            # Данных нет в БД
            print("INFO: БД пустая (первый запуск)")
```

**Гипотеза 2:** deal_key mismatch между Excel и БД
```python
# Диагностика
async def compare_deal_keys():
    excel_deals = await parser.parse_file("test.xlsx")
    db_deals = await repository.find_by_period("01", "2025")
    
    excel_keys = {d.deal_key for d in excel_deals}
    db_keys = {d.deal_key for d in db_deals}
    
    only_in_excel = excel_keys - db_keys
    only_in_db = db_keys - excel_keys
    
    print(f"Only in Excel: {len(only_in_excel)}")
    for key in list(only_in_excel)[:5]:
        print(f"  {key}")
    
    print(f"Only in DB: {len(only_in_db)}")
    for key in list(only_in_db)[:5]:
        print(f"  {key}")
    
    # Проверить, есть ли схожие ключи (отличие в пробелах)
    for excel_key in only_in_excel:
        for db_key in only_in_db:
            similarity = SequenceMatcher(None, excel_key, db_key).ratio()
            if similarity > 0.9:
                print(f"MATCH: {similarity:.2%}")
                print(f"  Excel: {repr(excel_key)}")
                print(f"  DB:    {repr(db_key)}")
```

**Гипотеза 3:** hash_key некорректно вычисляется
```python
# Проверка детерминированности hash_key
def test_hash_key_determinism():
    deal1 = Deal(
        client_name="Test Client",
        invoice_number="123",
        seller="John",
        period=Period(month="01", year="2025"),
        items=[],
    )
    
    hash1 = deal1.hash_key
    
    # Пересоздать deal с теми же данными
    deal2 = Deal(
        client_name="Test Client",
        invoice_number="123",
        seller="John",
        period=Period(month="01", year="2025"),
        items=[],
    )
    
    hash2 = deal2.hash_key
    
    assert hash1 == hash2, f"Hash mismatch: {hash1} != {hash2}"
    
    # Проверить влияние пробелов
    deal3 = Deal(
        client_name=" Test Client ",  # Пробелы
        invoice_number="123",
        seller="John",
        period=Period(month="01", year="2025"),
        items=[],
    )
    
    hash3 = deal3.hash_key
    print(f"Hash with spaces: {hash1} vs {hash3}")
```

---

### Этап 2: Исправление BUG-002 (has_totals_error)

**Файл:** `src/infrastructure/workers/read_model_builder.py`

**Шаги:**
1. Изучить текущую логику `_recalculate_totals` (строки 1170-1210)
2. Изучить правильную логику в `Deal.has_totals_error` (domain/models/deal.py)
3. Привести infrastructure логику в соответствие с domain
4. Добавить unit tests

**Код исправления:**
```python
async def _recalculate_totals(self, deal_id: uuid.UUID) -> None:
    """Recalculate aggregated totals with correct NULL handling."""
    
    # 1. Get declared totals (from Excel)
    src_result = await self.session.execute(
        select(
            ReadModelDeal.total_revenue_amount,
            ReadModelDeal.total_margin_amount,
            ReadModelDeal.total_cost_amount,
        ).where(ReadModelDeal.id == deal_id)
    )
    src_row = src_result.one_or_none()
    if not src_row:
        return
    
    src_rev, src_mar, src_cost = src_row
    
    # 2. Calculate totals from positions
    calc_result = await self.session.execute(
        select(
            func.count(ReadModelPosition.id),
            func.coalesce(func.sum(ReadModelPosition.quantity), Decimal("0")),
            func.coalesce(func.sum(ReadModelPosition.revenue_amount), Decimal("0")),
            func.coalesce(func.sum(ReadModelPosition.margin_amount), Decimal("0")),
            func.coalesce(func.sum(ReadModelPosition.cost_amount), Decimal("0")),
        ).where(ReadModelPosition.deal_id == deal_id)
    )
    calc_row = calc_result.one()
    items_cnt, qty, calc_rev, calc_mar, calc_cost = calc_row
    
    # 3. Determine has_totals_error with correct NULL handling
    #    Logic matches Domain model: Deal.has_totals_error
    
    if items_cnt == 0:
        # No items → no calculated totals → no error
        has_error = None
    else:
        # All declared totals are NULL (no_cash mode)
        all_declared_null = (
            src_rev is None and src_mar is None and src_cost is None
        )
        
        if all_declared_null:
            # NULL = no data to compare (not an error)
            has_error = None
        else:
            # Compare declared (not NULL) with calculated
            def _has_mismatch(declared: Decimal | None, calculated: Decimal) -> bool:
                if declared is None:
                    # NULL declared = no requirement to match
                    return False
                return abs(declared - calculated) > Decimal("0.01")
            
            has_error = any(
                _has_mismatch(declared, calculated)
                for declared, calculated in [
                    (src_rev, calc_rev),
                    (src_mar, calc_mar),
                    (src_cost, calc_cost),
                ]
            )
    
    # 4. Update deal with calculated values
    await self.session.execute(
        update(ReadModelDeal)
        .where(ReadModelDeal.id == deal_id)
        .values(
            items_count=items_cnt,
            total_quantity=qty,
            calc_revenue_amount=calc_rev if items_cnt > 0 else None,
            calc_margin_amount=calc_mar if items_cnt > 0 else None,
            calc_cost_amount=calc_cost if items_cnt > 0 else None,
            has_totals_error=has_error,
        )
    )
    
    logger.debug(
        f"Recalculated totals for deal {deal_id}: "
        f"items={items_cnt}, has_error={has_error}"
    )
```

**Tests:**
```python
@pytest.mark.asyncio
async def test_has_totals_error_with_null_declared():
    """Test that NULL declared totals don't trigger has_totals_error."""
    
    # Setup: Deal with NULL totals (no_cash mode)
    deal = Deal(
        client_name="Test",
        seller="John",
        period=Period(month="01", year="2025"),
        total_revenue=None,  # NULL
        total_margin=None,   # NULL
        total_cost=None,     # NULL
        items=[
            DealItem(
                product_name="Product 1",
                quantity=Decimal("10"),
                revenue=Money(amount=Decimal("1000")),
                margin=SignedMoney5(amount=Decimal("200")),
                cost=Money(amount=Decimal("800")),
            )
        ],
    )
    
    # Calculated totals
    assert deal.calc_revenue_amount == Money(amount=Decimal("1000"))
    assert deal.calc_margin_amount == SignedMoney(amount=Decimal("200"))
    assert deal.calc_cost_amount == Money(amount=Decimal("800"))
    
    # has_totals_error should be None (not True!)
    assert deal.has_totals_error is None, (
        "Expected has_totals_error=None when all declared totals are NULL"
    )


@pytest.mark.asyncio
async def test_has_totals_error_with_mismatch():
    """Test that mismatch triggers has_totals_error."""
    
    deal = Deal(
        client_name="Test",
        seller="John",
        period=Period(month="01", year="2025"),
        total_revenue=Money(amount=Decimal("999")),  # Declared: 999
        total_margin=None,
        total_cost=None,
        items=[
            DealItem(
                product_name="Product 1",
                revenue=Money(amount=Decimal("1000")),  # Calculated: 1000
                margin=SignedMoney5(amount=Decimal("200")),
                cost=Money(amount=Decimal("800")),
            )
        ],
    )
    
    # Mismatch: 999 vs 1000
    assert deal.has_totals_error is True, (
        "Expected has_totals_error=True when declared != calculated"
    )


@pytest.mark.asyncio
async def test_has_totals_error_with_match():
    """Test that matching totals don't trigger error."""
    
    deal = Deal(
        client_name="Test",
        seller="John",
        period=Period(month="01", year="2025"),
        total_revenue=Money(amount=Decimal("1000")),  # Matches calculated
        items=[
            DealItem(
                product_name="Product 1",
                revenue=Money(amount=Decimal("1000")),
            )
        ],
    )
    
    assert deal.has_totals_error is False
```

---

### Этап 3: Исправление BUG-001 (Audit)

**Приоритет:** Средний (после BUG-002 и BUG-003)

**Опции:**

**Option A: Удалить return (простое решение)**
```python
async def _create_audit_entry(...):
    try:
        logger.debug(f"Audit entry: {entity_type} {change_type}")
        # return  <-- УДАЛИТЬ
        
        audit_entry = ReadModelAudit(...)
        self.session.add(audit_entry)
```

**Option B: Feature flag (рекомендуемое)**
```python
# Config
class ReadModelBuilderConfig(BaseModel):
    enable_audit: bool = False  # По умолчанию выключен
    audit_async: bool = True     # Асинхронная запись через очередь

# Implementation
async def _create_audit_entry(...):
    if not self.config.enable_audit:
        logger.debug(f"Audit disabled: {entity_type} {change_type}")
        return
    
    if self.config.audit_async:
        # Non-blocking: enqueue to background worker
        await self.audit_queue.enqueue({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "change_type": change_type,
            ...
        })
    else:
        # Blocking: write immediately
        audit_entry = ReadModelAudit(...)
        self.session.add(audit_entry)
```

**Option C: Separate audit service (лучшая архитектура)**
```python
# Domain event
class DomainEvent:
    event_type: str
    aggregate_id: UUID
    data: dict

# Audit subscriber
class AuditEventSubscriber:
    async def on_event(self, event: DomainEvent):
        audit_entry = ReadModelAudit(
            entity_type=event.aggregate_type,
            entity_id=event.aggregate_id,
            ...
        )
        await self.audit_repository.save(audit_entry)

# Event bus
event_bus.subscribe("DealCreated", audit_subscriber.on_event)
event_bus.subscribe("DealItemAdded", audit_subscriber.on_event)
```

---

## ЧАСТЬ 6: ВЫВОДЫ И РЕКОМЕНДАЦИИ

### 6.1 Общий вердикт

План анализа выполнен на **высоком профессиональном уровне** с небольшими пробелами в области производительности и транзакционной модели.

**Сильные стороны:**
- ✅ Детальная структура анализа по компонентам
- ✅ Корректная идентификация критических багов
- ✅ Понимание Event Sourcing + CQRS архитектуры
- ✅ Практические рекомендации по исправлению

**Области улучшения:**
- ⚠️ Добавить раздел о производительности и масштабируемости
- ⚠️ Рассмотреть транзакционную консистентность
- ⚠️ Добавить сценарии disaster recovery
- ⚠️ Расширить тестовое покрытие в плане

---

### 6.2 Финальные рекомендации

1. **Немедленно исправить:**
   - BUG-002 (has_totals_error с NULL) → КРИТИЧЕСКИЙ бизнес-баг
   - Провести диагностику BUG-003 (event_store) → причина всех проблем

2. **Среднесрочно:**
   - Внедрить feature flag для BUG-001 (audit)
   - Добавить транзакционные границы в ReadModelBuilder
   - Оптимизировать batch processing событий

3. **Долгосрочно:**
   - Внедрить Snapshot механизм для Event Store
   - Добавить distributed locking для параллельных синхронизаций
   - Создать comprehensive test suite (unit + integration + E2E)
   - Внедрить мониторинг (Prometheus + Grafana)

4. **Архитектурные улучшения:**
   - Вынести бизнес-логику из Infrastructure в Domain
   - Создать Domain Services для сложной логики
   - Внедрить Builder validation
   - Добавить Saga pattern для транзакционности

---

### 6.3 Оценка проекта в целом

**Архитектура:** 8/10
- Отличное применение DDD, Event Sourcing, CQRS
- Четкое разделение слоев
- Небольшие утечки бизнес-логики в Infrastructure

**Код:** 7.5/10
- Чистый, читаемый код
- Хорошие docstrings
- Найдены критические баги (нормально для сложных систем)

**Тестирование:** 6/10 (требует улучшения)
- Есть базовые integration tests
- Не хватает unit tests для Domain logic
- Нет property-based testing

**Производительность:** 7/10
- Есть оптимизации (hash_key, индексы)
- Нужен batch processing
- Нет профилирования узких мест

**Общая оценка проекта: 7.5/10** - Хороший проект с солидной архитектурой, требует устранения критических багов и оптимизации производительности.

---

**Конец документа**

