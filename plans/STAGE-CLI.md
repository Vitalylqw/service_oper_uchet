# STAGE-CLI: CLI-обёртка `so-uchet`

## Цель этапа

Создать единую CLI-точку входа для всех операций приложения:
синхронизация, снапшоты, дашборды, управление БД.

CLI заменяет необходимость вызывать отдельные Python-скрипты вручную
и становится стандартным способом взаимодействия внешних приложений и
операторов с системой.

## Что входит в scope

- entry point `so-uchet` в `pyproject.toml`;
- модуль `src/cli/` как presentation layer;
- команды: `sync`, `snapshot`, `dashboard`, `db`;
- единая инициализация: конфигурация, логирование, подключение к БД;
- стабильность, подробное логирование, обработка ошибок;
- обновление проектной документации.

## Что НЕ входит в scope

- изменение бизнес-логики sync flow;
- рефакторинг domain / application / infrastructure слоёв;
- удаление или перемещение существующих скриптов;
- добавление новых бизнес-функций (REST API, UI и т.п.);
- изменение схемы БД или миграций.

## Принятые решения

| Решение | Обоснование |
|---------|-------------|
| Фреймворк: `click` | Зрелый, стабильный, минимум магии, широко используется |
| Имя CLI: `so-uchet` | Совпадает с именем пакета, легко запоминается |
| Расположение: `src/cli/` | Отдельный presentation layer, не смешивается с DDD-слоями |
| Старые скрипты: остаются на месте | Не ломаем существующие workflow, CLI — дополнение |
| Log level по умолчанию: DEBUG | Для sync-команд максимальная детализация по умолчанию |
| Файл по умолчанию | `data/real_data_for_testing/Data_source_excel.xlsx` |

## Ограничения и риски

1. Dashboard-скрипты используют sync SQLAlchemy (psycopg2), а sync flow — async.
   CLI должен корректно работать с обоими режимами.
2. Конфигурация окружения (`config.env` vs `.env`) не унифицирована.
   CLI должен использовать существующую схему загрузки без её переделки.
3. Зависимость `click` должна быть добавлена в `pyproject.toml`.
4. Существующие скрипты могут содержать неработающий код.
   CLI должен строиться на проверенной логике, а не копировать скрипты 1:1.

---

## Этап 1. Каркас CLI + команда `db`

### Цель

Создать инфраструктуру CLI и первую рабочую группу команд.

### Задачи

1. Добавить `click` в зависимости `pyproject.toml`.
2. Создать структуру `src/cli/`:
   - `__init__.py`
   - `main.py` — корневая группа команд
   - `db.py` — команды работы с БД
   - `common.py` — общие утилиты (инициализация логирования, загрузка конфигурации)
3. Зарегистрировать entry point `so-uchet` в `pyproject.toml`:
   ```
   [project.scripts]
   so-uchet = "cli.main:cli"
   ```
4. Реализовать команды:
   - `so-uchet db test` — проверка подключения к БД
   - `so-uchet db migrate` — `alembic upgrade head`
   - `so-uchet db align [--apply-fixes] [--stamp]` — выравнивание схемы
5. Реализовать общую инициализацию:
   - загрузка `config.env` в окружение
   - настройка loguru с уровнем из CLI-параметра
   - корректная обработка ошибок с понятными сообщениями

### Проверка

- `so-uchet --help` выводит список групп команд.
- `so-uchet db test` выполняется и сообщает о статусе подключения.
- `so-uchet db migrate` выполняет `alembic upgrade head`.
- `so-uchet db align --apply-fixes --stamp` выполняет выравнивание.
- Ошибки подключения обрабатываются без traceback в stdout.

### Ожидаемые файлы

```
src/cli/__init__.py
src/cli/main.py
src/cli/common.py
src/cli/db.py
```

---

## Этап 2. Команды `sync`

### Цель

Перенести синхронизацию из скриптов в CLI с улучшением стабильности.

### Задачи

1. Создать `src/cli/sync.py`.
2. Реализовать фабрику сервисов — функцию, которая создаёт и связывает
   все необходимые сервисы (parser, detector, orchestrator, repos, builder)
   в рамках одной async-сессии.
3. Реализовать команды:

   **`so-uchet sync full`**
   - `--file PATH` — путь к Excel-файлу (по умолчанию: `data/real_data_for_testing/Data_source_excel.xlsx`)
   - `--log-level [DEBUG|INFO]` — уровень логирования (по умолчанию: DEBUG)
   - Выполняет полную синхронизацию всех листов.

   **`so-uchet sync partial`**
   - `--file PATH` — путь к Excel-файлу (по умолчанию: стандартный)
   - `--last-periods N` — количество последних периодов (по умолчанию: 12)
   - `--log-level [DEBUG|INFO]` — уровень логирования (по умолчанию: DEBUG)
   - Логика: парсит Excel → получает все листы → сортирует по дате (убывание) → берёт N последних.

   **`so-uchet sync periods`**
   - `--file PATH` — путь к Excel-файлу (по умолчанию: стандартный)
   - `--periods TEXT...` — конкретные периоды, например `"Январь 2025" "Февраль 2025"`.
     По умолчанию: последний период.
   - `--log-level [DEBUG|INFO]` — уровень логирования (по умолчанию: DEBUG)

   **`so-uchet sync status`**
   - Показывает текущую или последнюю сессию синхронизации.

   **`so-uchet sync list`**
   - `--limit N` — количество записей (по умолчанию: 10)
   - Показывает историю сессий.

4. Обеспечить корректный exit code: 0 при успехе, 1 при ошибке.
5. После синхронизации выводить краткую сводку в консоль.

### Проверка

- `so-uchet sync full` отрабатывает на реальном Excel-файле.
- `so-uchet sync partial --last-periods 3` берёт 3 последних периода.
- `so-uchet sync periods --periods "Январь 2025"` синхронизирует один период.
- `so-uchet sync status` показывает последнюю сессию.
- `so-uchet sync list` показывает историю.
- При отсутствии файла — понятное сообщение об ошибке.

### Ожидаемые файлы

```
src/cli/sync.py
```

---

## Этап 3. Команды `snapshot`

### Цель

Управление снапшотами БД через CLI.

### Задачи

1. Создать `src/cli/snapshot.py`.
2. Реализовать команды:

   **`so-uchet snapshot create`**
   - `--label NAME` — метка снапшота (по умолчанию: auto-генерация с timestamp)
   - `--source NAME` — источник (по умолчанию: `cli`)
   - Использует существующую логику `db_snapshot_service.py`.
   - Выводит сводку: кол-во deals, positions, периодов, health issues.

   **`so-uchet snapshot list`**
   - `--limit N` — количество записей (по умолчанию: 20)
   - Выводит таблицу: id, label, дата, deals, positions.

3. Для переиспользования логики — импортировать напрямую из `dashboard/`
   (добавить в `sys.path` если нужно), не копируя код.

### Проверка

- `so-uchet snapshot create --label test_cli` создаёт снапшот.
- `so-uchet snapshot list` показывает список.
- Ошибки подключения обрабатываются корректно.

### Ожидаемые файлы

```
src/cli/snapshot.py
```

---

## Этап 4. Команды `dashboard`

### Цель

Генерация HTML-отчётов через CLI.

### Задачи

1. Создать `src/cli/dashboard.py`.
2. Реализовать команды:

   **`so-uchet dashboard latest`**
   - `--no-browser` — не открывать в браузере
   - Генерирует HTML-отчёт по последнему снапшоту.

   **`so-uchet dashboard compare`**
   - `--label1 X --label2 Y` — сравнение по меткам
   - `--id1 N --id2 N` — сравнение по id
   - `--no-browser`
   - Без аргументов: сравнивает два последних снапшота.

   **`so-uchet dashboard excel-health`**
   - `--file PATH` — путь к Excel (по умолчанию: стандартный)
   - `--periods TEXT...` — периоды для анализа (по умолчанию: все)
   - `--threshold N` — порог расхождения в рублях
   - `--no-browser`
   - Генерирует Excel Health Dashboard (health-check + сравнение с БД).

3. Для переиспользования — импортировать логику из `dashboard/`.

### Проверка

- `so-uchet dashboard latest` генерирует HTML и сообщает путь.
- `so-uchet dashboard compare` сравнивает два снапшота.
- `so-uchet dashboard excel-health` генерирует health-отчёт.
- `--no-browser` подавляет открытие в браузере.

### Ожидаемые файлы

```
src/cli/dashboard.py
```

---

## Этап 5. Финализация и документация

### Цель

Стабилизация, проверка, обновление документации, закрытие этапа.

### Задачи

1. Прогон всех CLI-команд, проверка стабильности.
2. Обновление документации:
   - `project_progress/PROJECT_OVERVIEW.md` — CLI в архитектуре
   - `project_progress/STATUS.md` — результаты этапа
   - `project_progress/SYNC_FLOW.md` — обновить точки входа
   - `project_progress/DEVELOPMENT_JOURNAL.md` — запись о реализации
   - `docs/DEVELOPMENT_GUIDE.md` — раздел про CLI-команды
3. Обновление `plans/STAGE-CLI.md` — фиксация результатов.
4. Commit по Conventional Commits.

### Проверка

- Все команды из этого плана работают.
- Документация соответствует реализации.
- `ruff check .` без ошибок для новых файлов.

---

## Полная карта CLI-команд

```
so-uchet
  sync
    full      [--file PATH] [--log-level DEBUG|INFO]
    partial   [--file PATH] [--last-periods N] [--log-level DEBUG|INFO]
    periods   [--file PATH] [--periods TEXT...] [--log-level DEBUG|INFO]
    status
    list      [--limit N]
  snapshot
    create    [--label NAME] [--source NAME]
    list      [--limit N]
  dashboard
    latest    [--no-browser]
    compare   [--label1 X --label2 Y | --id1 N --id2 N] [--no-browser]
    excel-health [--file PATH] [--periods TEXT...] [--threshold N] [--no-browser]
  db
    test
    migrate
    align     [--apply-fixes] [--stamp]
```

## Зависимости между этапами

```
Этап 1 (каркас + db)
  └── Этап 2 (sync)     — использует common.py из Этапа 1
  └── Этап 3 (snapshot)  — использует common.py из Этапа 1
  └── Этап 4 (dashboard) — использует common.py из Этапа 1
        └── Этап 5 (финализация) — после всех предыдущих
```

Этапы 2, 3, 4 могут идти в любом порядке после Этапа 1.
