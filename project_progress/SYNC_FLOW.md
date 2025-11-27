Процесс синхронизации данных (от Excel до read‑моделей)

Цель

- Импортировать данные из Excel, зафиксировать их как события (Event Sourcing), построить и
  обновить read‑модели (CQRS) для быстрых запросов и отчётности.

Точка входа

- Приложение/скрипт вызывает `SyncOrchestratorService.execute_sync(file_path, config)`.
- В тестовом сценарии вход — `testing/scripts/test_sync_integration.py → main() → execute_sync()`.

Основные участники (объекты/классы)

- `SyncOrchestratorService` — оркестратор полного процесса.
- `ExcelParserService` — парсинг Excel в доменные модели `Deal`/`DealItem`.
- `ChangeDetectorService` — определение изменений (для инкрементальной синхронизации).
- `EventStoreImplementation` — запись и чтение событий из таблицы `event_store`.
- `ReadModelBuilder` — построение/обновление read‑моделей по событиям.
- `SyncSessionRepositoryImplementation` — хранение состояния сессии синхронизации.
- `DatabaseManager/DatabaseConfig` — доступ к БД и сессии.

Конфигурация (входные параметры)

- `SyncConfiguration` (основные поля):
  - `sync_type: "full" | "incremental"`
  - `incremental_period_months: int` (для инкрементальной синхронизации)
  - `create_events: bool` (создавать ли события)
  - `update_read_models: bool` (обновлять ли read‑модели по событиям)
  - `continue_on_errors`, `rollback_on_failure` (политика ошибок)

Пошаговый сценарий

1) Инициализация окружения и зависимостей

- Вызов: создание `DatabaseManager` и получение `AsyncSession`.
- Создаются сервисы: `ExcelParserService`, `ChangeDetectorService`, `EventStoreImplementation`,
  `SyncSessionRepositoryImplementation`, `ReadModelBuilder`.
- Выход: все сервисы готовы к работе.
- Следующая точка: создание и сохранение сессии синхронизации.

2) Создание сессии синхронизации

- Вызов: `SyncOrchestratorService._create_sync_session(session_id, file_path, config)`.
- Логика:
  - Проверка отсутствия уже запущенной сессии (`get_running_session`).
  - Заполнение метаданных файла (размер, md5‑хеш; при недоступности — безопасные значения).
  - Установка статуса `pending`/`running`, запись в `sync_sessions` через репозиторий.
- Выход: строка в `sync_sessions` со статусом «в процессе».
- Следующая точка: парсинг Excel.

3) Парсинг Excel

- Вызов: `ExcelParserService.parse_file(file_path, sync_session) → ParseResult`.
- Логика:
  - Чтение всех листов, определение заголовка, извлечение периода из имени листа.
  - Формирование списка `Deal` (мастер‑строки) и `DealItem` (позиции), расчёт недостающих полей.
  - Сбор статистики (`ParseStats`), привязка к `sync_session`.
- Выход: `ParseResult` с `deals: list[Deal]`, статистикой и метаданными файла.
- Следующая точка: определение изменений (для `incremental`) либо немедленная генерация событий (для `full`).

4) Определение изменений (только для incremental)

- Вызов: `ChangeDetectorService.detect_changes(deals, incremental_period_months)`.
- Логика: сравнение с текущим состоянием/политикой периода, формирование наборов: вставки,
  обновления (с `field_changes`), удаления.
- Выход: структура `ChangeDetectionResult` с подсчётами и деталями изменений.
- Следующая точка: генерация событий.

5) Формирование событий

- Вызов: `SyncOrchestratorService._apply_changes_to_database(result, config)`.
- Логика:
  - Для `full`: по каждой сделке — событие `DealCreated`, по каждой её позиции — `DealItemAdded`.
  - Для `incremental`: согласно `ChangeDetectionResult` — `DealCreated`/`DealUpdated`/`DealDeleted`.
  - Каждое событие — словарь вида `{aggregate_id, event_type, event_data, metadata}`:
    - `aggregate_id` — идентификатор агрегата, у нас это всегда `Deal.id` (UUID сделки).
      Все события одной сделки сгруппированы по этому ID и применяются по порядку.
    - `event_type` — тип события (например, `DealCreated`, `DealItemAdded`, `DealUpdated`,
      `DealDeleted`). Определяет какой обработчик будет вызван в `ReadModelBuilder`.
    - `event_data` — полезная нагрузка события:
      - `DealCreated.event_data`: идентификаторы и поля сделки (+ totals, period и др.).
      - `DealItemAdded.event_data`: `deal_id`, `item_id`, реквизиты позиции, цены/количества.
    - `metadata` — служебные сведения (идентификатор сессии, тип синхронизации, источник и т.п.).
- Выход: список событий в памяти.
- Следующая точка: запись событий в `event_store`.

6) Запись событий в Event Store

- Вызов: `EventStoreImplementation.append_events(events)`.
- Логика:
  - Для каждого события определяется `aggregate_type` и следующий `sequence_number` в рамках
    `aggregate_id` (ID сделки).
  - Вставка записей в таблицу `event_store` (`processed_at IS NULL`).
- Выход: события зафиксированы транзакционно в `event_store`.
- Следующая точка: построение/обновление read‑моделей по событиям.

Пояснение терминов:

- `aggregate_type` — строковый тип агрегата, выводимый из `event_type` (например, для
  `DealCreated` и `DealItemAdded` это `Deal`). Используется для индексации и аналитики.
- `sequence_number` — монотонный номер события внутри одного `aggregate_id`. Гарантирует, что
  события для одной сделки будут обработаны в строгом порядке их появления.

7) Обновление read‑моделей (CQRS)

- Вызов: `ReadModelBuilder.process_latest_events(limit, auto_commit)`.
- Получение партии необработанных событий: `EventStore.get_latest_events(limit)`
  (упорядочено по `(aggregate_id, sequence_number)`).
- Обработка событий:
  - Deal‑события:
    - `DealCreated` → `_create_deal_read_model`: upsert в `read_deals` с денормализацией.
    - `DealUpdated` → `_update_deal_read_model` по `field_changes` (без версий в read_deals).
    - `DealDeleted` → `_delete_deal_read_model` (жесткое удаление) с каскадом на позиции.
    - `DealWithPositionsCreated` (если используется) → `_sync_deal_with_positions` с
      пакетной синхронизацией позиций через `PositionSyncLogic`.
  - DealItem‑события:
    - `DealItemAdded` → `_create_deal_item_read_model`: создание/версионирование записи в
      `read_positions`, денормализация контекста сделки, предотвращение дубликатов по `hash_key`.
    - `DealItemUpdated` → `_update_deal_item_read_model` (включая смену `hash_key` с
      деактивацией старой версии и созданием новой активной).
    - `DealItemDeleted` → `_delete_deal_item_read_model` (мягкое удаление) + пересчёт итогов.
  - Sync‑события:
    - `SyncSessionCompleted` → `_update_stats_after_sync`: запись агрегатов в `read_stats`.
- Пересчёт агрегатов сделки: `_recalculate_totals(deal_id)` суммирует активные позиции и
  обновляет рассчитанные суммы/дельты и флаг ошибок.
- Отложенные события (deferred):
  - Если позиция пришла до появления родителя в `read_deals`, событие добавляется в
    `DeferredEventQueue` с причиной «родитель не найден». Очередь хранится в памяти и имеет
    стратегию повторов с дифференцированной задержкой.
  - После основного прохода вызывается обработка готовых к повтору элементов очереди.
- Маркировка обработки: после успешной обработки каждого события выставляется `processed_at` в
  `event_store`.
- Выход: `read_deals`, `read_positions`, `read_stats` приведены в актуальное состояние; события
  отмечены обработанными.
- Следующая точка: завершение сессии синхронизации.

О лимите выборки `limit` и «последних» событиях

- `limit` — параметр, ограничивающий объём выборки за один проход. Передаётся из оркестратора,
  в типовом запуске равен `1_000_000` (см. `SyncOrchestratorService._apply_changes_to_database`).
- Если `limit` меньше количества необработанных событий, за один вызов обрабатывается только часть,
  остальные остаются с `processed_at IS NULL` и будут обработаны следующим вызовом.
- «Последними» считаются все записи с `processed_at IS NULL`. Метод
  `get_latest_events` выбирает именно их и сортирует по `(aggregate_id, sequence_number)` для
  корректного порядка внутри каждой сделки.

Два чётких потока: полная vs инкрементальная синхронизация

Полная синхронизация (`sync_type = "full"`):

1. Парсинг Excel → `ParseResult.deals` (все сделки и их позиции).
2. Генерация событий: для каждой сделки — `DealCreated`; для каждой позиции — `DealItemAdded`.
3. Запись всей партии событий в `event_store` одной транзакцией.
4. Обработка событий `ReadModelBuilder`:
   - `DealCreated` → upsert в `read_deals`.
   - `DealItemAdded` → вставка/обновление/версионирование в `read_positions` с денормализацией
     контекста:
     - Получаем контекст сделки (`deal_key`, `client_name`, период). Если родителя нет в
       `read_deals` — событие откладывается (deferred) с причиной «родитель не найден».
     - Формируем запись позиции: ключевые поля `id`, `deal_id`, `deal_key`, `position_number`,
       `hash_key` (полный, включает `deal_key` и `position_number`), реквизиты товара и суммы.
     - Ищем активную запись с тем же `hash_key`:
       - Если найдена и тот же `deal_id` → выполняется UPDATE существующей записи (без изменения
         `id` и `hash_key`), инкрементируется `version = version + 1`.
       - Если найдена, но другой `deal_id` → предыдущая активная запись деактивируется
         (`is_active = false`, `version = old + 1`), затем создаётся НОВАЯ запись с тем же
         `hash_key`, `is_active = true`, `version = old + 2` (перенос позиции к другому родителю).
       - Если не найдена активная запись → выполняется INSERT с `version = 1`, `is_active = true`.
     - После вставки/обновления выполняется пересчёт агрегатов сделки
       (`_recalculate_totals(deal_id)`).
5. Установка `processed_at` для обработанных событий.
6. Завершение сессии: статус `completed`, фиксация метрик.

Инкрементальная синхронизация (`sync_type = "incremental"`):

1. Парсинг Excel → `ParseResult.deals` (подмножество по периоду/источнику).
2. Определение изменений `ChangeDetectorService.detect_changes()` → наборы вставок/обновлений/
   удалений и `field_changes`.
3. Генерация событий по изменениям:
   - Вставки: `DealCreated`.
   - Обновления: `DealUpdated` c `field_changes`.
   - Удаления: `DealDeleted`.
4. Запись событий в `event_store`.
5. Обработка событий `ReadModelBuilder`:
   - `DealCreated` → upsert в `read_deals` (как в полной синхронизации).
   - `DealUpdated` → адресное обновление строки сделки в `read_deals`:
     - По `deal_id` извлекается текущая запись; если не найдена — логируется предупреждение,
       обновление пропускается (upsert не выполняется).
     - `field_changes` маппятся на соответствующие поля (например, `client_name`, `invoice_info`,
       статусы, суммы, `period_*`).
     - Выполняется UPDATE и инкрементируется `version = version + 1`, проставляется `updated_at`.
     - При необходимости выполняется пересчёт агрегатов.
   - `DealDeleted` → мягкое удаление (soft delete):
     - В `read_deals`: `is_active = false`, `version = version + 1`.
     - В `read_positions` всех позиций этой сделки: `is_active = false`, `version = version + 1`.
   - Позиции при инкременте (если приходят события на позиции):
     - `DealItemAdded` → как в полной синхронизации (вставка/обновление/версионирование).
     - `DealItemUpdated` →
       - Если `hash_key` (содержимое позиции) не изменился → простой UPDATE полей и
         `version = version + 1`.
       - Если `hash_key` изменился → текущая запись деактивируется, и создаётся новая активная
         версия с обновлённым `hash_key` (инвариант уникальности по активному `hash_key` сохраняется).
     - `DealItemDeleted` → мягкое удаление позиции: `is_active = false`, `version = version + 1`.
6. Установка `processed_at` для обработанных событий, завершение сессии.

8) Завершение сессии

- Вызов: `SyncOrchestratorService._complete_sync_session(sync_session, success)`.
- Логика: установка финального статуса (`completed`/`failed`), сохранение в `sync_sessions`.
- Выход: консистентная запись о сессии, тайминги и итоговые метрики.
- Следующая точка: использование read‑моделей и статистики внешними потребителями (отчёты, UI).

Форматы данных (ключевые)

- `ParseResult`:
  - `deals: list[Deal]`, `stats: ParseStats`, `sync_session`, `file_path`, `file_size`, `file_hash`,
    `parsed_at`.
- Событие `DealCreated` (поля в `event_data`): `deal_id`, `deal_key`, реквизиты клиента/счёта,
  `period`, статусы, `totals`.
- Событие `DealItemAdded` (поля в `event_data`): `deal_id`, `item_id`, `product_name`,
  `supplier_name`, `pickup_date`, `quantity`, `position_number`, `prices` (purchase/sale/revenue/
  margin/cost).

Структура ParseResult (подробно)

- `ParseResult`:
  - `deals: list[Deal]`
  - `stats: ParseStats`
  - `sync_session: SyncSession`
  - `file_path: str`
  - `file_size: int`
  - `file_hash: str`
  - `parsed_at: datetime`

Схема (упрощённая):
```json
{
  "deals": [ { /* Deal */ } ],
  "stats": { /* ParseStats */ },
  "sync_session": { /* SyncSession */ },
  "file_path": "...",
  "file_size": 0,
  "file_hash": "...",
  "parsed_at": "ISO8601"
}
```

Транзакции и порядок

- Запись событий в `event_store` — батчем, транзакционно.
- Чтение для обработки — по `processed_at IS NULL`, упорядочено по `(aggregate_id, sequence_number)`
  для сохранения причинно‑следственного порядка внутри одной сделки.
- Обновления read‑моделей выполняются в рамках текущей async‑сессии; после батча возможен commit.

Логирование и наблюдаемость

- Подробные логи на каждом этапе (старт/завершение фаз, статистика парсинга, число созданных
  событий, количество обработанных и отложенных событий, состояние очереди, сводки по read‑моделям).
- Предупреждения при отложении событий с указанием причины и идентификаторов.

Известные нюансы

- Отложенная очередь `DeferredEventQueue` является оперативной (в памяти процесса). Если процесс
  завершается до повторной обработки, элементы очереди теряются, а соответствующие события уже
  помечены как обработанные в `event_store`. Это проектное решение — для тестов/one‑shot запусков
  может потребоваться явное «дожатие» очереди (или альтернативная стратегия без отложенной очереди).

Выходные данные (итоги процесса)

- `sync_sessions`: зафиксированная история сессии (статус, файл, длительность, статистика).
- `event_store`: события синхронизации с выставленным `processed_at` после обработки.
- `read_deals`: денормализованные сделки с агрегатами; без версионности и soft‑delete.
- `read_positions`: денормализованные позиции (уникальность через `hash_key`, версионирование,
  признак активности).
- `read_stats`: агрегаты по сессии/периодам (для дашбордов и отчётности).

Следующие точки использования

- Отчёты/дашборды/поисковые запросы используют `read_*` таблицы (CQRS: быстрые чтения).
- Интеграционные тесты и скрипты верифицируют числа и консистентность по `read_*` и `event_store`.


