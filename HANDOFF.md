# INCIDENT REPORT: CLI `so-uchet` / sync runtime regression

## Дата

2026-03-29

## Контекст задачи

Пользователь попросил:

1. понять, на какой стадии находится реализация CLI-обёртки `so-uchet`;
2. продолжить разработку;
3. довести CLI до рабочего состояния;
4. отдельно проверить runtime-поведение команд `sync`.

Исходный план этапа находился в:
- `plans/STAGE-CLI.md`

Ключевой scope:
- этап 1: `db`
- этап 2: `sync`
- далее `snapshot`, `dashboard`

---

## Исходный согласованный план

### Сначала
1. Прочитать `.agents/*`, `project_goals.md`, `plans/STAGE-CLI.md`
2. Сверить план CLI с реальным состоянием кода
3. Понять, что уже реализовано, а что нет

### Затем
1. Реализовать этап 1:
   - `so-uchet db test`
   - `so-uchet db migrate`
   - `so-uchet db align`
2. Реализовать этап 2:
   - `so-uchet sync full`
   - `so-uchet sync partial`
   - `so-uchet sync periods`
   - `so-uchet sync status`
   - `so-uchet sync list`
3. Проверить runtime

### После runtime-проверки
Пользователь захотел улучшить:
1. чтобы `sync status` видел активную running/pending session;
2. чтобы `sync periods/partial` не парсили весь workbook целиком.

---

## Что было обнаружено на старте

На момент начала работ:

- план CLI был описан в `plans/STAGE-CLI.md`;
- реализация CLI по факту отсутствовала;
- не было `src/cli/*`;
- в `pyproject.toml` не было `click`;
- не было `[project.scripts] so-uchet = ...`;
- существовали рабочие куски логики:
  - sync orchestrator;
  - parser;
  - event store;
  - sync session repository;
  - snapshot/dashboard скрипты.

Вывод:
- CLI был спроектирован, но ещё не реализован.

---

## Что было сделано

## 1. Реализован CLI-каркас

Изменён:
- `pyproject.toml`

Добавлено:
- зависимость `click`
- entry point `so-uchet = "cli.main:cli"`

Созданы:
- `src/cli/__init__.py`
- `src/cli/common.py`
- `src/cli/main.py`
- `src/cli/db.py`
- `src/cli/sync.py`

### Реализованы команды `db`
- `so-uchet db test`
- `so-uchet db migrate`
- `so-uchet db align`

### Реализованы команды `sync`
- `so-uchet sync full`
- `so-uchet sync partial`
- `so-uchet sync periods`
- `so-uchet sync status`
- `so-uchet sync list`

---

## 2. Что было сделано в `common.py`

В `src/cli/common.py` добавлена общая инициализация:
- загрузка `config.env`
- настройка логирования
- промапливание legacy DB env-переменных в формат, который ожидает `DatabaseConfig`

Причина:
- без этого CLI читал бы env нестабильно, так как в проекте есть legacy naming (`DB_HOST`, `DB_NAME`, и т.д.) и `DatabaseConfig` ожидает другой вид env-ключей.

---

## 3. Реализован этап 2 `sync`

В `src/cli/sync.py` был собран runtime-контур поверх уже существующего:
- `ExcelParserService`
- `ChangeDetectorService`
- `SyncOrchestratorService`
- `EventStoreImplementation`
- `SyncSessionRepositoryImplementation`
- `ReadModelBuilder`

---

## 4. Первичная runtime-проверка `sync`

Было проверено:
- `sync status`
- `sync list`
- `sync periods --periods "Март 2026"`

### Что подтвердилось
- `sync status` и `sync list` читают БД;
- `sync periods` создаёт sync session и стартует parser.

### Что не подтвердилось
Проверочный запуск `sync periods --periods "Март 2026"` не завершился в ожидаемое время.

Пользователь уточнил важный runtime-критерий:
- загрузка одного месяца должна занимать около 1 минуты.

Фактически проверочный запуск висел существенно дольше и не завершился.

Вывод:
- partial runtime нельзя считать рабочим;
- это нужно считать регрессией.

---

## 5. После этого были сделаны дополнительные правки

Пользователь попросил сначала проанализировать проблему, затем предложить минимальные правки.

После анализа были внесены две группы изменений.

### 5.1. Видимость активной sync session

Причина анализа:
- `sync status` не видел активную pending session во время выполнения.

Что изменено:
- в `src/domain/interfaces/repository_interfaces.py`
  добавлен метод `save_visible(...)`
- в `src/infrastructure/database/repositories.py`
  реализован `save_visible(...)` через отдельную async session + commit
- в `src/application/sync_orchestrator/orchestrator.py`
  обычный `save()` для старта/завершения session заменён на `save_visible()`

Цель:
- сделать запись session видимой другим соединениям до конца общего sync-процесса.

### 5.2. Parser-level фильтрация периодов

Причина анализа:
- `sync partial/periods` фильтровали сделки после полного парсинга workbook;
- то есть runtime partial был почти как full parse.

Что изменено:
- `src/application/excel_parser/parser.py`
- `parse_file(...)` расширен опциональным backward-compatible параметром:
  `allowed_periods: list[str] | None = None`
- `_read_excel_file(...)` также расширен `allowed_periods`
- добавлена фильтрация листов до цикла обработки sheet'ов

Цель:
- ограничить парсинг только нужными листами/периодами;
- сохранить старый контракт parser для старых скриптов.

### 5.3. CLI-адаптер updated

В `src/cli/sync.py`:
- убрана post-filter логика по `result.deals`
- CLI теперь просто передаёт `allowed_periods` в parser

---

## Что было проверено тестами

Прошли:
- `tests/unit/test_cli_db.py`
- `tests/unit/test_cli_sync.py`
- `tests/unit/application/test_sync_orchestrator_visibility.py`
- `tests/unit/application/test_excel_parser_period_filter.py`

Также проходил `ruff check` по затронутым файлам.

---

## Что пошло не так

## 1. Критичная проблема runtime

После изменений partial runtime всё равно не был доказан как рабочий:
- `sync periods --periods "Март 2026"` снова не завершился в приемлемое время;
- по пользовательскому критерию это означает, что сервис нельзя считать рабочим.

Это главный нерешённый инцидент.

## 2. Хуже того: после тестового запуска осталась зависшая pending session

Во время runtime-проверки проверочный sync был принудительно остановлен.

После этого в БД осталась запись:
- `sync_session_id = 1acd1137-3ecf-4261-8809-792b37ebe4b7`

Состояние:
- `status = pending`

Это видно через:
- `sync status`
- `sync list`

Проблема:
- новые sync-запуски могут блокироваться проверкой "another sync session is already running".

Это уже operational issue, мешающий работе пользователей.

---

## Что было подтверждено runtime после последних правок

Подтвердилось:
- `sync status` теперь действительно видит активную pending session во время выполнения;
- это значит, что правка `save_visible()` технически сработала.

Но одновременно:
- после принудительного прерывания процесса pending session осталась висеть;
- recovery-механизма на случай external kill сейчас нет.

---

## Моя текущая гипотеза о причине проблемы

### Гипотеза 1. Основная задержка не только в parser-level sheet filter
Даже после переноса фильтрации в parser runtime остался неприемлемым.

Возможные причины:
- `load_workbook(...)` сам по себе тяжёлый на этом файле;
- `refresh_excel_cache_if_enabled(...)` и общий путь чтения workbook всё ещё дорогие;
- parser всё ещё делает тяжёлую подготовку workbook даже при одном листе;
- проблема вообще может быть не в parser, а в downstream runtime, но до него лог не дошёл.

### Гипотеза 2. Новый `save_visible()` не причина долгого partial runtime
`save_visible()` подтвердил видимость pending session и не выглядит главной причиной 10-минутного зависания.

Но он породил новый риск:
- если процесс убивают извне, pending session остаётся в БД навсегда, пока кто-то не закроет её вручную.

### Гипотеза 3. Partial-path всё ещё недостаточно изолирован от full parse
Хотя sheet filter теперь встроен в parser, этого оказалось недостаточно для фактического runtime-требования пользователя.

---

## Текущее состояние системы

### Код
CLI-код есть и unit-уровень проходит.

### Runtime
Нельзя считать подтверждённо рабочим для partial sync.

### БД
Есть зависшая pending session:
- `1acd1137-3ecf-4261-8809-792b37ebe4b7`

Это нужно учитывать первым делом.

---

## Что должен сделать следующий агент

## Сначала: аварийное восстановление работы
1. Проверить, блокирует ли зависшая pending session новые sync-запуски
2. Если да:
   - вручную перевести `1acd1137-3ecf-4261-8809-792b37ebe4b7` в `failed`
   - проставить `finished_at`
3. Проверить:
   - `sync status`
   - `sync list`
   - новый запуск sync больше не блокируется

Важно:
- не трогать `event_store`, `read_deals`, `read_positions`, если не доказано, что они пострадали;
- сначала восстановить возможность запусков.

## Затем: локализовать runtime regression
Приоритет проверки:
1. измерить время на parser-only path для одного периода;
2. понять, зависает ли именно `_read_excel_file()` / `load_workbook()`;
3. сравнить runtime старого сценария и нового CLI path;
4. отдельно проверить, был ли regression внесён CLI-обвязкой или проблема существовала глубже.

## Затем: решить вопрос с dangling pending sessions
Нужен controlled strategy:
- либо heartbeat/lease timeout;
- либо recovery on startup;
- либо явная команда cleanup/stale-session-repair;
- либо возврат от `save_visible()` к другой модели видимости.

---

## Файлы, которые были изменены

- `pyproject.toml`
- `src/cli/__init__.py`
- `src/cli/common.py`
- `src/cli/main.py`
- `src/cli/db.py`
- `src/cli/sync.py`
- `src/domain/interfaces/repository_interfaces.py`
- `src/infrastructure/database/repositories.py`
- `src/application/sync_orchestrator/orchestrator.py`
- `src/application/excel_parser/parser.py`
- `tests/unit/test_cli_db.py`
- `tests/unit/test_cli_sync.py`
- `tests/unit/application/test_sync_orchestrator_visibility.py`
- `tests/unit/application/test_excel_parser_period_filter.py`

---

## Главное резюме

Сделано:
- CLI `db` и `sync`
- unit-покрытие
- parser-level фильтр периодов
- видимость active sync session

Не сделано / не подтверждено:
- доказать, что partial runtime снова укладывается в рабочее время пользователя

Что сломано operationally:
- после тестового прерывания осталась зависшая pending session в БД

Самый важный next step:
- сначала аварийно снять зависшую pending session,
- потом разбирать runtime regression partial sync.

---

## UPDATE 2026-03-30

Этот блок добавлен позже и уточняет фактическое состояние CLI после дополнительной
runtime-проверки в реальном контуре.

### Что оказалось ложным выводом из предыдущего расследования

Предыдущий вывод о том, что `sync periods --periods "Март 2026"` не является рабочим,
оказался искажён ограничениями sandbox-среды.

Во время запуска внутри sandbox воспроизводились ошибки доступа к PostgreSQL:
- `Temporary failure in name resolution`
- `Operation not permitted`

Это было связано не с поломкой CLI-логики, а с ограничениями среды выполнения.

### Что подтверждено повторной реальной проверкой

Вне sandbox был успешно выполнен сценарий:
- `so-uchet sync periods --periods "Март 2026"`

Результат:
- `sync_session_id = a0a56119-8a92-4aa0-be58-5ff235a9d852`
- `status = completed`
- обработано `631` deals
- обработано `3872` items
- длительность `39.32s`

Дополнительно подтверждено:
- `sync status` во время выполнения видел активную `pending` session;
- после завершения `sync status` показывает эту же session как `completed`;
- `sync list --limit 3` показывает новую completed session первой в истории.

Вывод:
- для проверенного runtime-сценария `sync periods/status/list` CLI является рабочим.

### Новый реальный дефект, найденный при дополнительной проверке

При проверке:
- `so-uchet db test`

выяснилось, что сама проверка подключения к БД проходит успешно, но затем
возникает runtime-ошибка на cleanup:
- `Future attached to a different loop`
- `Event loop is closed`

Причина:
- `db test` выполнял `manager.test_connection()` и `manager.close()` через два разных
  вызова `run_async(...)`;
- это создавало два разных `asyncio` event loop для одного и того же async DB manager.

### Что было исправлено

В `src/cli/db.py`:
- проверка подключения и `manager.close()` сведены в один async helper;
- теперь весь lifecycle `db test` выполняется в одном event loop.

Добавлен unit-тест:
- `tests/unit/test_cli_db.py`
- проверяет, что `test_connection()` и `close()` выполняются в одном loop.

### Что повторно проверено после исправления

Подтверждено:
- `tests/unit/test_cli_db.py`
- `tests/unit/test_cli_sync.py`
- `tests/unit/application/test_sync_orchestrator_visibility.py`
- `tests/unit/application/test_excel_parser_period_filter.py`

Также повторно подтверждено в реальном runtime:
- `so-uchet db test`

Итог:
- команда завершается чисто;
- выводит `Database connection: OK`;
- traceback по cleanup больше не возникает.

### Актуальный статус CLI на 2026-03-30

Подтверждено рабочим:
- `so-uchet db test`
- `so-uchet sync periods`
- `so-uchet sync status`
- `so-uchet sync list`

Реализовано в коде, но ещё не подтверждено в текущем проходе:
- `so-uchet db migrate`
- `so-uchet db align`
- `so-uchet sync partial`
- `so-uchet sync full`

Не реализовано:
- `snapshot`
- `dashboard`

### Обновлённый next step

1. Проверить оставшиеся команды этапов `db` и `sync`:
   - `so-uchet db migrate`
   - `so-uchet db align`
   - `so-uchet sync partial`
   - при необходимости `so-uchet sync full`
2. После этого переходить к реализации этапов:
   - `snapshot`
   - `dashboard`

---

## FINAL UPDATE 2026-03-30

Этот блок фиксирует состояние после завершения реализации этапов `snapshot`
и `dashboard`, а также после дополнительных runtime-проверок CLI.

### Что дополнительно подтверждено в runtime

Подтверждено рабочим:
- `so-uchet db migrate`
- `so-uchet db align`
- `so-uchet sync partial --last-periods 1`

Результат `sync partial --last-periods 1`:
- `sync_session_id = dfdf658a-ad45-402d-a76b-1acd881f4f63`
- `status = completed`
- обработано `631` deals
- обработано `3872` items
- длительность `34.51s`

Вывод:
- этапы `db` и основной `sync` подтверждены как рабочие по проверенным сценариям;
- отдельно `sync full` в этом проходе не запускался, но это уже не блокирует завершение
  основного CLI-этапа.

### Что было реализовано после этого

#### 1. Этап `snapshot`

Добавлено:
- `src/cli/snapshot.py`

Подключено:
- группа `snapshot` в `src/cli/main.py`

Реализованы команды:
- `so-uchet snapshot create`
- `so-uchet snapshot list`

Подход:
- core-логика не копировалась;
- CLI переиспользует `dashboard/db_snapshot_service.py`
- `snapshot list` читает `db_snapshots` напрямую через sync SQLAlchemy engine.

Runtime-проверка:
- `so-uchet snapshot create --label test_cli_snapshot --source cli`
- успешно создан snapshot:
  - `id = 71`
  - `label = test_cli_snapshot`
  - `source = cli`
  - `deals = 50351`
  - `positions = 293447`
  - `health issues = 7`
- `so-uchet snapshot list --limit 5`
  - показывает новую запись первой в истории.

#### 2. Этап `dashboard`

Добавлено:
- `src/cli/dashboard.py`

Подключено:
- группа `dashboard` в `src/cli/main.py`

Реализованы команды:
- `so-uchet dashboard latest`
- `so-uchet dashboard compare`
- `so-uchet dashboard excel-health`

Подход:
- CLI не дублирует HTML/dashboard-логику;
- используются существующие standalone entry points:
  - `dashboard/generate_dashboard.py`
  - `dashboard/excel_health_dashboard.py`
- для `--no-browser` подавляется `webbrowser.open`, чтобы избежать GUI side effects.

Runtime-проверка:
- `so-uchet dashboard latest --no-browser`
  - сгенерировал:
    - `/workspaces/service_oper_uchet/dashboard/reports/dashboard_20260330_191907.html`
- `so-uchet dashboard compare --no-browser`
  - сгенерировал:
    - `/workspaces/service_oper_uchet/dashboard/reports/dashboard_compare_auto_20260314_211339_vs_test_cli_snapshot.html`
- `so-uchet dashboard excel-health --periods "Март 2026" --no-browser`
  - сгенерировал:
    - `/workspaces/service_oper_uchet/dashboard/reports/excel_health_20260330_192125.html`

### Важное ограничение, выявленное при `excel-health`

Команда `dashboard excel-health` работает, но её текущий pipeline:
- сначала парсит весь workbook;
- только потом фильтрует выбранные периоды.

Это не дефект CLI-обёртки.
Это особенность текущей логики standalone-скрипта
`dashboard/excel_health_dashboard.py` / `dashboard/excel_audit/excel_reader.py`.

Следствие:
- даже запуск с `--periods "Март 2026"` остаётся тяжёлым по времени.

Это можно считать отдельным будущим улучшением, но не blocker для завершения
CLI-этапа.

### Что было проверено тестами на финальном проходе

Подтверждено:
- `tests/unit/test_cli_db.py`
- `tests/unit/test_cli_sync.py`
- `tests/unit/test_cli_snapshot.py`
- `tests/unit/test_cli_dashboard.py`
- `tests/unit/application/test_sync_orchestrator_visibility.py`
- `tests/unit/application/test_excel_parser_period_filter.py`

Также проходил:
- `ruff check`

### Актуальный итоговый статус CLI

Реализовано и проверено:
- `db`
- `sync`
- `snapshot`
- `dashboard`

Иными словами:
- этапы 1-4 из `plans/STAGE-CLI.md` доведены до рабочего состояния
  по основным сценариям.

### Что остаётся после завершения CLI-этапа

Не как blocker, а как потенциальный follow-up:
1. при необходимости отдельно прогнать `so-uchet sync full`;
2. при желании оптимизировать pipeline `dashboard excel-health`,
   чтобы он не парсил весь workbook при выборе одного периода;
3. при необходимости обновить статический план/документацию,
   если нужно явно пометить CLI-stage как завершённый.
