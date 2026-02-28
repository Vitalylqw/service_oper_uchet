# ПЛАН АНАЛИЗА СИСТЕМЫ СИНХРОНИЗАЦИИ ДАННЫХ

**Дата создания:** 29 ноября 2025  
**Статус:** В работе  
**Обновлено:** 29 ноября 2025 (добавлены результаты первичного анализа)

---

## РЕЗУЛЬТАТЫ ПЕРВИЧНОГО АНАЛИЗА (КРИТИЧЕСКИЕ НАХОДКИ)

### ПОДТВЕРЖДЕННЫЕ БАГИ

#### BUG-001: `_create_audit_entry` никогда не создает записи [КРИТИЧЕСКИЙ]

**Файл:** `src/infrastructure/workers/read_model_builder.py`, строка 1225

**Проблема:** В методе `_create_audit_entry` есть оператор `return` ПЕРЕД кодом создания записи:

```python
async def _create_audit_entry(...):
    try:
        if additional_data:
            logger.debug(...)
        else:
            logger.debug(...)
        return  # <-- БАГ: код ниже никогда не выполнится!
        
        audit_entry = ReadModelAudit(...)  # Недостижимый код
        self.session.add(audit_entry)
```

**Влияние:** Таблица `read_audit` никогда не заполняется. Это объясняет проблему из TODO.MD.

**Исправление:** Удалить `return` на строке 1225.

---

#### BUG-002: `has_totals_error` некорректно обрабатывает NULL [КРИТИЧЕСКИЙ]

**Файл:** `src/infrastructure/workers/read_model_builder.py`, строки 1183-1189

**Проблема:** Функция `_delta` превращает `NULL` в `0`:

```python
def _delta(src: Decimal | None, calc: Decimal) -> Decimal:
    return abs((src or Decimal("0")) - calc)  # NULL → 0

has_error = any(
    _delta(val, calc) > Decimal("0.01")
    for val, calc in ((src_rev, rev), (src_mar, mar), (src_cost, cost))
)
```

**Пример ошибки:**
- Excel: `total_revenue = NULL` (режим no_cash)
- Calculated: `calc_revenue = 1000.00` (сумма позиций)
- `_delta(NULL, 1000) = abs(0 - 1000) = 1000`
- `1000 > 0.01` → `has_error = True`

**Ожидаемое поведение:** Если `total_revenue = NULL`, не сравнивать с calc_revenue.

**Логика в Domain модели (Deal.has_totals_error) - ПРАВИЛЬНАЯ:**
```python
if self.total_revenue is None and self.total_margin is None and self.total_cost is None:
    return None  # Не ошибка, просто нет данных
```

**Исправление:** Привести логику `_recalculate_totals` в соответствие с Domain:
```python
def _delta(src: Decimal | None, calc: Decimal) -> bool:
    if src is None:
        return False  # NULL не считается ошибкой
    return abs(src - calc) > Decimal("0.01")

# Если все totals = NULL, has_error = None (не True)
if src_rev is None and src_mar is None and src_cost is None:
    has_error = None
else:
    has_error = any(_delta(val, calc) for val, calc in ...)
```

---

#### BUG-003: Потенциальная проблема с deal_key при загрузке из БД [СРЕДНИЙ]

**Файл:** `src/infrastructure/database/repositories.py`, строки 244-261

**Проблема:** При загрузке Deal из БД через `_read_model_to_domain`, deal_key **пересчитывается** из полей, а не берется из сохраненного `model.deal_key`:

```python
builder = DealBuilder(period=period)
builder.invoice_number = model.invoice_number or None  # None vs ""?
builder.invoice_date = model.invoice_date or None      # None vs ""?
builder.seller = model.seller or "UNKNOWN"             # Fallback!
deal = builder.build()  # deal_key вычисляется заново
```

**Риск:** Если при сохранении и загрузке есть разница в нормализации (пробелы, None vs "", UNKNOWN fallback), deal_key может не совпасть.

**Нужна проверка:** Сравнить `model.deal_key` с `deal.deal_key` после загрузки.

---

### ПРОВЕРЕННЫЕ ГИПОТЕЗЫ

| Гипотеза | Результат | Комментарий |
|----------|-----------|-------------|
| `find_by_period` неправильно вызывается | НЕТ | Порядок аргументов правильный: `find_by_period(month, year)` |
| Периоды некорректно парсятся | НЕТ | `period_key = f"{year}-{month}"`, split работает корректно |
| События создаются для неизмененных данных | ЧАСТИЧНО | При первом запуске (БД пустая) это нормально. Проблема может быть в deal_key mismatch |

---

## ЧАСТЬ 1: ЦЕЛИ И ЗАДАЧИ ПРОЕКТА

### 1.1 Основная цель проекта

Создать систему автоматической синхронизации данных о сделках из Excel-файлов в базу данных с возможностью:
- Отслеживания изменений между синхронизациями
- Хранения истории всех изменений (Event Sourcing)
- Быстрого доступа к актуальному состоянию данных (CQRS Read Models)
- Верификации корректности данных (сравнение declared vs calculated totals)

### 1.2 Функциональные требования

| Требование | Описание | Статус |
|------------|----------|--------|
| FR-01 | Парсинг Excel файлов с формулами и кэшированными значениями | Реализовано |
| FR-02 | Определение периода из названия листа | Реализовано |
| FR-03 | Создание сделок (Deal) с позициями (DealItem) | Реализовано |
| FR-04 | Детекция изменений между парсингом и БД | Реализовано |
| FR-05 | Генерация событий только для измененных данных | Проблема |
| FR-06 | Хранение событий в Event Store | Реализовано |
| FR-07 | Построение read-моделей из событий | Реализовано |
| FR-08 | Пересчет агрегатов (calc_*) по позициям | Реализовано |
| FR-09 | Флаг has_totals_error при расхождении total_* и calc_* | Проблема |
| FR-10 | Аудит изменений в read_audit | Не работает |
| FR-11 | Поддержка 5-знаковой точности для purchase_price и margin | Реализовано |

### 1.3 Нефункциональные требования

| Требование | Описание | Целевое значение |
|------------|----------|------------------|
| NFR-01 | Производительность парсинга | 1000+ строк/сек |
| NFR-02 | Производительность синхронизации | 100+ сделок/сек |
| NFR-03 | Точность финансовых расчетов | 5 знаков после запятой |
| NFR-04 | Идемпотентность синхронизации | Повторный запуск не дублирует данные |
| NFR-05 | Трассируемость изменений | Полная история в event_store |

### 1.4 Ожидаемый поток данных

```
Excel File
    │
    ▼
┌─────────────────┐
│  Excel Parser   │ → ParseResult (deals, items, stats)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Change Detector │ → ChangeDetectionResult (insertions, updates, deletions)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Sync Orchestrator│ → Events (DealCreated, DealItemAdded, etc.)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Event Store   │ → Persisted events with sequence_number
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Read Model      │ → read_deals, read_positions (актуальное состояние)
│ Builder         │ → read_audit (история изменений)
└─────────────────┘
```

---

## ЧАСТЬ 2: ЦЕЛИ И ЗАДАЧИ АНАЛИЗА

### 2.1 Цель анализа

Выявить ошибки, риски и неэффективности в процессе синхронизации данных для обеспечения:
- Корректности данных в read-моделях
- Оптимальной производительности
- Надежности и предсказуемости поведения

### 2.2 Задачи анализа

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| A-01 | Понять почему ВСЕ строки попадают в event_store независимо от изменений | Критический | ИССЛЕДУЕТСЯ (см. BUG-003) |
| A-02 | Найти причину неработающего has_totals_error при total_* = NULL | Критический | НАЙДЕНО (BUG-002) |
| A-03 | Понять почему не заполняется read_audit | Высокий | НАЙДЕНО (BUG-001) |
| A-04 | Проверить корректность change detection алгоритма | Высокий | Требует тестирования |
| A-05 | Оценить корректность hash_key вычислений | Средний | Требует тестирования |
| A-06 | Проверить обработку edge cases в парсере | Средний | Не начато |
| A-07 | Оценить производительность и найти узкие места | Низкий | Не начато |

### 2.3 Известные проблемы (из TODO.MD)

```
1. В режиме no_cash, поля total_*, заполняются Null, при этом возникает 
   несоответствие в полях calc_*. По идее должна включаться галочка 
   has_total_error. Но она не включается, видимо из-за того, что не 
   проходит операция с Null.

2. Проверить, почему в event_store попадают все строки из файла. 
   Независимо от того были изменения или нет. Ведь основная задача 
   перед обработкой сначала найти строки, которые были изменены и 
   потом уже их обрабатывать.

3. НЕ заполняется таблица read_audit в БД.

4. При изменении calc и has_total_error не происходит обновление 
   записей о сделках.
```

---

## ЧАСТЬ 3: АРХИТЕКТУРНЫЙ ОБЗОР (ЭТАП 1)

### 3.1 Цель этапа

Посмотреть на проект "сверху вниз" и убедиться, что:
- Все компоненты правильно организованы
- Взаимодействие между компонентами корректно
- Поток данных соответствует ожидаемому
- Нет архитектурных противоречий

### 3.2 Архитектурные слои и их назначение

#### Domain Layer (`src/domain/`)
**Назначение:** Чистая бизнес-логика без зависимостей от инфраструктуры

| Компонент | Ответственность |
|-----------|-----------------|
| `models/deal.py` | Агрегат Deal и сущность DealItem с бизнес-логикой |
| `value_objects/` | Money, Period, HashKey, Status - неизменяемые значения |
| `interfaces/` | Абстрактные интерфейсы (EventStore, Repository) |
| `exceptions/` | Доменные исключения |
| `builders/` | Паттерн Builder для создания Deal |

**Ключевые инварианты:**
- Deal.deal_key иммутабелен после создания
- DealItem.position_number уникален в рамках Deal
- calc_* вычисляются автоматически по items
- hash_key детерминированно вычисляется из полей

#### Application Layer (`src/application/`)
**Назначение:** Координация use cases, не содержит бизнес-логику

| Компонент | Ответственность |
|-----------|-----------------|
| `excel_parser/` | Парсинг Excel → Domain Models |
| `change_detector/` | Сравнение Excel данных с БД |
| `sync_orchestrator/` | Координация процесса синхронизации |
| `data_validator/` | Валидация данных |

**Принципы:**
- Получает данные от Infrastructure
- Вызывает Domain для бизнес-логики
- Не содержит SQL, не знает о структуре БД

#### Infrastructure Layer (`src/infrastructure/`)
**Назначение:** Реализация технических деталей (БД, файлы, внешние API)

| Компонент | Ответственность |
|-----------|-----------------|
| `database/connection.py` | Подключение к БД |
| `database/models.py` | SQLAlchemy модели (read_deals, read_positions, event_store) |
| `database/repositories.py` | Реализация Repository pattern |
| `database/event_store.py` | Реализация Event Store |
| `workers/read_model_builder.py` | Построение read-моделей из событий |
| `workers/simple_position_sync.py` | Упрощенная синхронизация позиций |
| `workers/deferred_event_queue.py` | Очередь отложенных событий |

### 3.3 Ключевые взаимодействия для проверки

```
┌────────────────────────────────────────────────────────────────┐
│                    SYNC ORCHESTRATOR                           │
│                                                                │
│  1. Создает SyncSession                                        │
│  2. Вызывает ExcelParser.parse_file()                          │
│  3. Вызывает ChangeDetector.detect_changes()                   │
│  4. Генерирует события на основе changes                       │
│  5. Записывает события в EventStore                            │
│  6. Вызывает ReadModelBuilder.process_latest_events()          │
│  7. Завершает SyncSession                                      │
└────────────────────────────────────────────────────────────────┘

КРИТИЧЕСКИЕ ТОЧКИ ПРОВЕРКИ:

[A] Parser → ChangeDetector
    - Формат Deal/DealItem должен быть идентичен тому, что ожидает detector
    - hash_key должен вычисляться одинаково

[B] ChangeDetector → Orchestrator  
    - ПРОБЛЕМА: Если detector возвращает все как "новые", все идет в event_store
    - Нужно проверить логику сравнения с БД

[C] Orchestrator → EventStore
    - События создаются только для insertions/updates/deletions
    - Если [B] сломан, здесь будут лишние события

[D] EventStore → ReadModelBuilder
    - Читает события с processed_at IS NULL
    - Маршрутизация по event_type

[E] ReadModelBuilder → Database
    - UPSERT логика для deals
    - UPSERT логика для positions
    - Пересчет totals
    - ПРОБЛЕМА: has_totals_error при NULL
    - ПРОБЛЕМА: audit не заполняется
```

### 3.4 Вопросы для архитектурного обзора

1. **Синхронизация hash_key:** Одинаково ли вычисляется hash_key в:
   - `Deal.hash_key` (domain)
   - `ChangeDetector._calculate_deal_hash()`
   - `ReadModelBuilder` при сохранении?

2. **Поток событий:** Почему в `_create_incremental_sync_events` создаются события для ВСЕХ insertions, а не только для реальных изменений?

3. **has_totals_error:** Как должна работать логика при `total_revenue = NULL`?
   - Вариант A: NULL означает "нет данных" → has_totals_error = NULL
   - Вариант B: NULL означает "0" → сравнивать с calc_*
   - Вариант C: NULL означает "ошибка" → has_totals_error = True

4. **read_audit:** Код записи audit существует, но закомментирован. Это намеренно?

---

## ЧАСТЬ 4: ДЕТАЛЬНЫЕ БЛОКИ АНАЛИЗА

### БЛОК 1: Excel Parser

#### 1.1 Назначение
Преобразование Excel файла в структурированные доменные объекты (Deal, DealItem) с сохранением точности финансовых данных.

#### 1.2 Входные данные
- Путь к Excel файлу
- SyncSession (опционально)

#### 1.3 Выходные данные
```python
ParseResult:
    deals: list[Deal]          # Список сделок с позициями
    stats: ParseStats          # Статистика парсинга
    file_path: str
    file_size: int
    file_hash: str             # MD5 хеш файла
```

#### 1.4 Ожидаемое поведение

1. **Определение периода:**
   - Извлекает период из названия листа (например, "Январь 2025")
   - Если формат невалидный - лист пропускается
   
2. **Парсинг заголовков:**
   - Ищет строку с "Клиент" в первых 5 строках
   - Определяет структуру колонок

3. **Парсинг данных:**
   - Master record (строка с client_name) → создает Deal
   - Detail records (строки без client_name) → создает DealItem
   - position_number инкрементируется для каждого item в рамках deal

4. **Обработка формул:**
   - CacheMode.CACHE_ONLY: только кэшированные значения
   - CacheMode.NO_CACHE: пропуск формул
   - CacheMode.HYBRID: xlcalculator + fallback на кэш

5. **Финансовые данные:**
   - purchase_price, margin → Money5 (5 знаков)
   - sale_price, revenue, cost → Money (2 знака)
   - Decimal из float для сохранения точности

#### 1.5 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K1.1 | Все листы с валидным периодом обработаны |
| K1.2 | Количество deals = количество master records |
| K1.3 | Количество items = количество detail records |
| K1.4 | position_number уникален в рамках deal |
| K1.5 | Финансовые поля сохраняют точность из Excel |
| K1.6 | Формулы вычислены или взяты из кэша |

#### 1.6 Потенциальные риски

- **R1.1:** Потеря точности float → Decimal
- **R1.2:** Некорректное определение заголовка
- **R1.3:** Неверный период из названия листа
- **R1.4:** xlcalculator не справляется со сложными формулами

---

### БЛОК 2: Change Detector

#### 2.1 Назначение
Сравнение данных из Excel (ParseResult) с текущим состоянием в БД для определения:
- Какие сделки/позиции новые (INSERT)
- Какие изменились (UPDATE)
- Какие удалены (DELETE)

#### 2.2 Входные данные
```python
excel_deals: list[Deal]        # Результат парсинга
sync_period_months: int        # Период для инкрементальной синхронизации (не используется в новой логике)
```

#### 2.3 Выходные данные
```python
ChangeDetectionResult:
    insertions: list[EntityChange]    # Новые сущности
    updates: list[EntityChange]       # Измененные сущности
    deletions: list[EntityChange]     # Удаленные сущности
    total_excel_deals: int
    total_db_deals: int
```

#### 2.4 Ожидаемое поведение

1. **Загрузка данных из БД:**
   ```python
   # Извлекаем периоды из Excel
   excel_periods = {f"{deal.period.year}-{deal.period.month}" for deal in excel_deals}
   
   # Загружаем сделки только для этих периодов
   db_deals = await repository.find_by_period(month, year)
   ```

2. **Построение hash-кэшей:**
   ```python
   excel_hashes = {deal.deal_key: _calculate_deal_hash(deal) for deal in excel_deals}
   db_hashes = {deal.deal_key: _calculate_deal_hash(deal) for deal in db_deals}
   ```

3. **Определение изменений для сделок:**
   ```python
   for deal_key in excel_hashes:
       if deal_key not in db_hashes:
           # INSERT
       elif excel_hashes[deal_key] != db_hashes[deal_key]:
           # UPDATE с детальным сравнением полей
   
   for deal_key in db_hashes:
       if deal_key not in excel_hashes:
           # DELETE
   ```

4. **Определение изменений для позиций:**
   - Аналогичная логика с использованием `get_full_hash_key(deal_key)`

#### 2.5 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K2.1 | Загружаются только сделки за релевантные периоды |
| K2.2 | hash вычисляется идентично для Excel и БД данных |
| K2.3 | INSERT только для deal_key, отсутствующих в БД |
| K2.4 | UPDATE только при реальном изменении hash |
| K2.5 | DELETE только для deal_key, отсутствующих в Excel |
| K2.6 | field_changes содержит только измененные поля |

#### 2.6 Потенциальные риски

- **R2.1 (КРИТИЧНО):** Если `find_by_period` не находит сделки в БД (или возвращает пустой список), ВСЕ excel_deals будут помечены как INSERT
- **R2.2:** Разница в вычислении hash между Excel и БД (разная точность Decimal)
- **R2.3:** Некорректная нормализация строк (пробелы, регистр)

---

### БЛОК 3: Sync Orchestrator

#### 3.1 Назначение
Координация полного процесса синхронизации: парсинг → детекция → события → read models.

#### 3.2 Входные данные
```python
file_path: str                    # Путь к Excel файлу
config: SyncConfiguration:
    sync_type: "full" | "partial"
    create_events: bool           # Создавать ли события
    update_read_models: bool      # Обновлять ли read models
    continue_on_errors: bool
    rollback_on_failure: bool
```

#### 3.3 Выходные данные
```python
SyncResult:
    sync_session_id: str
    parse_result: ParseResult
    change_detection_result: ChangeDetectionResult
    events_created: list[dict]
    summary: SyncSummary
```

#### 3.4 Ожидаемое поведение

1. **Создание сессии:**
   ```python
   sync_session = await _create_sync_session(session_id, file_path, config)
   # Проверяет, нет ли уже запущенной сессии
   ```

2. **Фаза парсинга:**
   ```python
   parse_result = await excel_parser.parse_file(file_path, sync_session)
   ```

3. **Фаза детекции:**
   ```python
   change_detection_result = await change_detector.detect_changes(
       parse_result.deals, 
       sync_period_months=0  # Не используется в новой логике
   )
   ```

4. **Генерация событий:**
   ```python
   # Для insertions: DealCreated + DealItemAdded для каждого item
   # Для updates: DealUpdated с field_changes
   # Для deletions: DealDeleted
   events = await _create_incremental_sync_events(result)
   ```

5. **Запись событий:**
   ```python
   await event_store.append_events(events)
   ```

6. **Обновление read models:**
   ```python
   await read_model_builder.process_latest_events(limit=1_000_000)
   ```

#### 3.5 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K3.1 | Только одна сессия может быть активна |
| K3.2 | События создаются ТОЛЬКО для изменений |
| K3.3 | Все события имеют корректный aggregate_id |
| K3.4 | При ошибке сессия завершается со статусом failed |
| K3.5 | read_models обновляются после записи событий |

#### 3.6 Потенциальные риски

- **R3.1:** rollback_on_failure не реализован (TODO в коде)
- **R3.2:** Если change_detector возвращает все как insertions, создается избыточное количество событий

---

### БЛОК 4: Event Store

#### 4.1 Назначение
Персистентное хранение доменных событий с поддержкой:
- Упорядочивания по sequence_number
- Фильтрации необработанных событий
- Upcasting (эволюция схемы событий)

#### 4.2 Входные данные (append)
```python
events: list[dict]:
    aggregate_id: UUID           # ID сделки
    event_type: str              # "DealCreated", "DealItemAdded", etc.
    event_data: dict             # Payload события
    metadata: dict               # sync_session_id, source, etc.
```

#### 4.3 Выходные данные (get_latest_events)
```python
events: list[dict]:
    event_id: UUID
    aggregate_id: UUID
    aggregate_type: str          # "Deal"
    event_type: str
    event_version: int           # Версия схемы события
    event_data: dict
    metadata: dict
    sequence_number: int         # Порядковый номер в рамках aggregate
    created_at: datetime
```

#### 4.4 Ожидаемое поведение

1. **Запись события:**
   ```python
   sequence_number = max(existing_sequence for aggregate_id) + 1
   aggregate_type = extract_from_event_type("DealCreated" → "Deal")
   INSERT INTO event_store (event_id, aggregate_id, aggregate_type, ...)
   ```

2. **Чтение необработанных:**
   ```python
   SELECT * FROM event_store 
   WHERE processed_at IS NULL
   ORDER BY aggregate_id, sequence_number  # Важно для консистентности
   LIMIT :limit
   ```

3. **Маркировка обработанных:**
   ```python
   UPDATE event_store SET processed_at = NOW() WHERE event_id = :id
   ```

#### 4.5 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K4.1 | sequence_number монотонно возрастает для aggregate |
| K4.2 | События одного aggregate обрабатываются в порядке sequence |
| K4.3 | Событие помечается processed_at после успешной обработки |
| K4.4 | Upcasting не теряет данные при эволюции схемы |

#### 4.6 Потенциальные риски

- **R4.1:** Race condition при параллельной записи (sequence_number)
- **R4.2:** Если обработка падает после изменения read model, но до processed_at - дублирование

---

### БЛОК 5: Read Model Builder

#### 5.1 Назначение
Построение и обновление денормализованных представлений (read_deals, read_positions) из событий Event Store.

#### 5.2 Входные данные
```python
events: list[dict]              # События из Event Store
limit: int                      # Количество событий за один проход
```

#### 5.3 Выходные данные
- Обновленные записи в read_deals
- Обновленные записи в read_positions
- Записи в read_audit (должно работать, но не работает)

#### 5.4 Ожидаемое поведение

1. **Маршрутизация событий:**
   ```python
   if event_type.startswith("DealItem"):
       await _handle_deal_item_event(...)
   elif event_type.startswith("Deal"):
       await _handle_deal_event(...)
   elif event_type.startswith("Sync"):
       await _handle_sync_event(...)
   ```

2. **Обработка DealCreated:**
   ```python
   # UPSERT в read_deals по deal_key
   INSERT INTO read_deals (...) 
   ON CONFLICT (deal_key) DO UPDATE SET ...
   
   # Пересчет totals
   await _recalculate_totals(deal_id)
   ```

3. **Обработка DealItemAdded:**
   ```python
   # Проверить, есть ли родительская сделка
   deal_context = await _get_deal_context(deal_id)
   if not deal_context:
       # DEFERRED: отложить обработку
       await deferred_queue.add_event(event, reason)
       return
   
   # UPSERT в read_positions по hash_key
   # Пересчет totals
   ```

4. **Пересчет totals:**
   ```python
   # Агрегация по позициям
   items_cnt, qty, rev, mar, cost = SELECT COUNT(*), SUM(quantity), ...
       FROM read_positions WHERE deal_id = :deal_id
   
   # Сравнение с declared totals
   has_error = any(abs(src - calc) > 0.01 for src, calc in ...)
   
   # Обновление deal
   UPDATE read_deals SET 
       items_count = :cnt,
       calc_revenue_amount = :rev,
       has_totals_error = :has_error
   WHERE id = :deal_id
   ```

5. **Маркировка обработки:**
   ```python
   UPDATE event_store SET processed_at = NOW() WHERE event_id = :id
   ```

#### 5.5 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K5.1 | Deal создается/обновляется при DealCreated |
| K5.2 | Position создается при DealItemAdded (если родитель существует) |
| K5.3 | Deferred events обрабатываются после появления родителя |
| K5.4 | calc_* пересчитываются при каждом изменении позиций |
| K5.5 | has_totals_error = True при расхождении > 0.01 |
| K5.6 | has_totals_error = NULL если все total_* = NULL |
| K5.7 | Событие помечается processed_at после обработки |
| K5.8 | read_audit содержит историю изменений |

#### 5.6 Потенциальные риски

- **R5.1 (КРИТИЧНО) - ПОДТВЕРЖДЕНО как BUG-001:** `_create_audit_entry` содержит `return` на строке 1225 ПЕРЕД созданием записи - audit никогда не создается. Код создания записи недостижим.

- **R5.2 (КРИТИЧНО) - ПОДТВЕРЖДЕНО как BUG-002:** Логика has_totals_error при NULL некорректна:
  ```python
  # Текущая логика в _recalculate_totals (НЕПРАВИЛЬНО):
  def _delta(src: Decimal | None, calc: Decimal) -> Decimal:
      return abs((src or Decimal("0")) - calc)  # NULL → 0!
  
  has_error = any(_delta(val, calc) > 0.01 for val, calc in ...)
  # Если src_rev=NULL и rev=1000, то _delta=1000, has_error=True
  
  # Правильная логика в Deal.has_totals_error:
  if all(t is None for t in [total_revenue, total_margin, total_cost]):
      return None  # Не ошибка, а "нет данных"
  ```

- **R5.3:** SimplePositionSync вызывает `commit()` внутри `_upsert_position()`, что создает много мелких транзакций и может конфликтовать с внешней транзакцией.

---

### БЛОК 6: Simple Position Sync

#### 6.1 Назначение
Упрощенная синхронизация позиций: UPSERT существующих, DELETE удаленных.

#### 6.2 Входные данные
```python
deal: Deal                      # Сделка с позициями
deal_context: dict              # deal_key, client_name, period_*
sync_session_id: UUID
```

#### 6.3 Выходные данные
```python
stats: dict:
    created: int
    updated: int
    deleted: int
```

#### 6.4 Ожидаемое поведение

1. **UPSERT позиций:**
   ```python
   for item in deal.items:
       hash_key = item.get_full_hash_key(deal_key)
       
       INSERT INTO read_positions (...)
       ON CONFLICT (hash_key) DO UPDATE SET ...
   ```

2. **DELETE удаленных:**
   ```python
   # Найти позиции, которых нет в parser
   existing = SELECT hash_key FROM read_positions WHERE deal_id = :deal_id
   to_delete = existing - parser_hash_keys
   
   DELETE FROM read_positions WHERE hash_key IN (:to_delete)
   ```

#### 6.5 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K6.1 | Все позиции из deal создаются/обновляются |
| K6.2 | Позиции, отсутствующие в deal, удаляются |
| K6.3 | hash_key вычисляется идентично парсеру |

#### 6.6 Потенциальные риски

- **R6.1:** `await self.session.commit()` внутри `_upsert_position` - много мелких коммитов

---

### БЛОК 7: Domain Models (Deal, DealItem)

#### 7.1 Назначение
Инкапсуляция бизнес-логики, вычисление производных полей, обеспечение инвариантов.

#### 7.2 Ключевые computed_field

```python
# Deal
id: UUID         = uuid5(namespace, deal_key)  # Детерминированный ID
deal_key: str    = f"{invoice_number}|{invoice_date}|{seller}|{period}"
hash_key: HashKey = MD5(all_fields + item_hashes)

calc_revenue_amount: Money = sum(item.revenue for item in items)
calc_margin_amount: SignedMoney = sum(item.margin for item in items)
calc_cost_amount: Money = sum(item.cost for item in items)
has_totals_error: bool | None = any(abs(total_* - calc_*) > 0.01)

# DealItem
id: UUID = uuid5(namespace, position_number + product_name + deal_key)
hash_key: HashKey = MD5(deal_key + position_number + product_name + ...)
full_hash_key: HashKey = MD5(all_fields + deal_key)  # Для уникальности в БД
```

#### 7.3 Критерии корректности

| Критерий | Проверка |
|----------|----------|
| K7.1 | deal_key иммутабелен после создания |
| K7.2 | id детерминированно вычисляется из deal_key |
| K7.3 | calc_* пересчитываются при изменении items |
| K7.4 | has_totals_error = NULL если все total_* = NULL |
| K7.5 | position_number уникален в рамках deal |

#### 7.6 Потенциальные риски

- **R7.1:** Разница в нормализации строк между парсером и моделью
- **R7.2:** Точность Decimal при вычислении hash_key

---

## ЧАСТЬ 5: ЧЕКЛИСТ ПРОВЕРКИ

### 5.1 Архитектурный уровень
- [ ] Все слои (Domain, Application, Infrastructure) изолированы
- [ ] Поток данных соответствует ожидаемому
- [ ] hash_key вычисляется одинаково во всех местах

### 5.2 Change Detection
- [ ] `find_by_period` возвращает данные из read_deals (не пустой список)
- [ ] Hash вычисляется с одинаковой точностью
- [ ] Только реальные изменения попадают в result

### 5.3 Event Store
- [ ] События создаются только для изменений
- [ ] sequence_number корректен
- [ ] processed_at устанавливается после обработки

### 5.4 Read Model Builder
- [ ] has_totals_error корректно обрабатывает NULL
- [ ] read_audit заполняется (раскомментировать код?)
- [ ] Deferred events обрабатываются

### 5.5 Database
- [ ] Индексы на hash_key, deal_key
- [ ] CASCADE DELETE для позиций
- [ ] Типы данных соответствуют Money5

---

## ЧАСТЬ 6: ПОРЯДОК ВЫПОЛНЕНИЯ АНАЛИЗА

| Этап | Описание | Приоритет |
|------|----------|-----------|
| 1 | Архитектурный обзор (Часть 3) | Высокий |
| 2 | Блок 2: Change Detector | Критический |
| 3 | Блок 5: Read Model Builder | Критический |
| 4 | Блок 1: Excel Parser | Средний |
| 5 | Блок 7: Domain Models | Средний |
| 6 | Блок 3: Sync Orchestrator | Средний |
| 7 | Блок 4: Event Store | Низкий |
| 8 | Блок 6: Simple Position Sync | Низкий |

---

## ЧАСТЬ 7: РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ

### 7.1 Немедленные исправления (Quick Fixes)

#### FIX-001: Включить создание audit записей
**Приоритет:** Высокий  
**Сложность:** Тривиальная  
**Файл:** `src/infrastructure/workers/read_model_builder.py`

```python
# Строка 1225: УДАЛИТЬ оператор return
async def _create_audit_entry(...):
    try:
        if additional_data:
            logger.debug(...)
        else:
            logger.debug(...)
        # return  <-- УДАЛИТЬ ЭТУ СТРОКУ
        
        audit_entry = ReadModelAudit(...)
        self.session.add(audit_entry)
```

#### FIX-002: Исправить логику has_totals_error для NULL
**Приоритет:** Критический  
**Сложность:** Средняя  
**Файл:** `src/infrastructure/workers/read_model_builder.py`

```python
async def _recalculate_totals(self, deal_id: uuid.UUID) -> None:
    # ... существующий код получения данных ...
    
    # НОВАЯ ЛОГИКА: Корректная обработка NULL
    def _has_mismatch(src: Decimal | None, calc: Decimal) -> bool:
        """Возвращает True если есть расхождение (NULL не считается расхождением)."""
        if src is None:
            return False
        return abs(src - calc) > Decimal("0.01")
    
    # Если все totals = NULL, это не ошибка, а отсутствие данных
    all_nulls = src_rev is None and src_mar is None and src_cost is None
    
    if all_nulls:
        has_error = None  # Нет данных для сравнения
    else:
        has_error = any(
            _has_mismatch(val, calc)
            for val, calc in ((src_rev, rev), (src_mar, mar), (src_cost, cost))
        )
    
    # Обновление с учетом NULL
    await self.session.execute(
        update(ReadModelDeal)
        .where(ReadModelDeal.id == deal_id)
        .values(
            items_count=items_cnt,
            total_quantity=qty,
            calc_revenue_amount=rev,
            calc_margin_amount=mar,
            calc_cost_amount=cost,
            has_totals_error=has_error,  # Теперь может быть None
        )
    )
```

### 7.2 Требуют дополнительного исследования

#### INV-001: Проблема с event_store (все данные как INSERT)
**Гипотеза:** deal_key при загрузке из БД не совпадает с deal_key из Excel.

**Шаги для проверки:**
1. Запустить синхронизацию дважды с одним файлом
2. После первого запуска проверить логи: `total_db_deals` должен быть > 0
3. Если `total_db_deals = 0`, проблема в `find_by_period`
4. Если `total_db_deals > 0`, но все как INSERT - проблема в deal_key mismatch

**Тестовый скрипт:**
```python
# Добавить в change_detector/detector.py для диагностики:
async def _get_database_deals(self, excel_deals, sync_period_months):
    # ... существующий код ...
    
    # DEBUG: Проверка совпадения deal_key
    for db_deal in db_deals:
        logger.debug(f"DB deal_key: {db_deal.deal_key}")
    for excel_deal in excel_deals:
        logger.debug(f"Excel deal_key: {excel_deal.deal_key}")
```

### 7.3 Порядок исправления

| Порядок | Задача | Время | Зависимости |
|---------|--------|-------|-------------|
| 1 | FIX-001: Включить audit | 5 мин | Нет |
| 2 | FIX-002: Исправить has_totals_error | 30 мин | Нет |
| 3 | INV-001: Диагностика event_store | 1-2 ч | FIX-001, FIX-002 |
| 4 | Тестирование всех исправлений | 1-2 ч | INV-001 |

---

## ПРИЛОЖЕНИЕ A: Файлы для анализа

```
src/
├── domain/
│   ├── models/deal.py                    # Deal, DealItem
│   ├── value_objects/common.py           # Money, Period, HashKey, Status
│   └── interfaces/                       # EventStore, Repository
├── application/
│   ├── excel_parser/parser.py           # ExcelParserService
│   ├── change_detector/detector.py      # ChangeDetectorService
│   └── sync_orchestrator/orchestrator.py # SyncOrchestratorService
└── infrastructure/
    ├── database/
    │   ├── models.py                     # SQLAlchemy models
    │   ├── event_store.py               # EventStoreImplementation
    │   └── repositories.py              # DealRepository
    └── workers/
        ├── read_model_builder.py        # ReadModelBuilder [БАГИ: BUG-001, BUG-002]
        ├── simple_position_sync.py      # SimplePositionSync
        └── deferred_event_queue.py      # DeferredEventQueue
```

---

## ПРИЛОЖЕНИЕ B: Контрольные тесты

### Тест 1: Проверка audit записей (после FIX-001)
```sql
-- После синхронизации должны появиться записи
SELECT COUNT(*) FROM read_audit;
SELECT entity_type, change_type, COUNT(*) 
FROM read_audit 
GROUP BY entity_type, change_type;
```

### Тест 2: Проверка has_totals_error (после FIX-002)
```sql
-- Сделки с total_* = NULL не должны иметь has_totals_error = True
SELECT deal_key, 
       total_revenue_amount, 
       calc_revenue_amount,
       has_totals_error
FROM read_deals
WHERE total_revenue_amount IS NULL
  AND has_totals_error = true;
-- Результат должен быть пустым
```

### Тест 3: Проверка change detection
```sql
-- После двойного запуска синхронизации с одним файлом:
SELECT event_type, COUNT(*) 
FROM event_store 
GROUP BY event_type;
-- При повторном запуске не должно быть новых DealCreated
```

