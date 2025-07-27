# План наведения порядка в файлах проекта

## Текущие проблемы

### 1. Файлы в корне проекта
- `excel_parser.py` - **ВАЖНЫЙ ФАЙЛ** (оставить в корне)
- `test_project_script_o3.py` - **ВАЖНЫЙ ФАЙЛ** (оставить в корне)
- `pydantic_settings/` - неправильно установленная зависимость
- `email_validator-2.0.0.dist-info/` - неправильно установленная зависимость
- `test.env` - должен быть `.env.example`

### 2. Дублирование bat файлов
- Корень: `start_api_server.bat`, `start_react_ui.bat`, `restart_servers.bat`
- `testing/`: дублирующие файлы

### 3. Неорганизованные скрипты
- Все скрипты в `scripts/` без категоризации
- Нужно разделить по назначению

## План действий

### Этап 1: Очистка корня проекта
1. **Оставить** `excel_parser.py` в корне (важный файл)
2. **Оставить** `test_project_script_o3.py` в корне (важный файл)
3. Удалить `pydantic_settings/` и `email_validator-2.0.0.dist-info/`
4. Переименовать `test.env` в `.env.example`

### Этап 2: Организация скриптов
Создать структуру в `scripts/`:
```
scripts/
├── debug/          # Отладочные скрипты
├── test/           # Тестовые скрипты
├── services/       # Сервисные скрипты
├── git/           # Git операции
└── database/      # Работа с БД
```

### Этап 3: Консолидация bat файлов
1. Оставить основные в корне
2. Удалить дублирующие из `testing/`
3. Создать единую точку запуска

### Этап 4: Очистка кэшей
Удалить:
- `__pycache__/`
- `.ruff_cache/`
- `.mypy_cache/`
- `.pytest_cache/`

## Структура после очистки

```
service_oper_uchet/
├── src/                    # Основной код
├── tests/                  # Тесты
├── docs/                   # Документация
├── data/                   # Данные
├── scripts/                # Скрипты (организованные)
├── testing/                # Тестирование (упрощенное)
├── .env.example           # Пример конфигурации
├── pyproject.toml         # Конфигурация проекта
├── requirements.txt       # Зависимости
├── README.md             # Основная документация
└── start_*.bat           # Основные bat файлы
```

## Статус выполнения
- [x] Этап 1: Очистка корня
- [x] Этап 2: Организация скриптов  
- [x] Этап 3: Консолидация bat файлов
- [x] Этап 4: Очистка кэшей

## Результаты

### Очищенные файлы:
- ✅ `pydantic_settings/` - удален (неправильно установленная зависимость)
- ✅ `email_validator-2.0.0.dist-info/` - удален (неправильно установленная зависимость)
- ✅ `test.env` - удален (дублировал .env.example)

### Сохраненные важные файлы:
- ✅ `excel_parser.py` - **СОХРАНЕН** (важный файл для проекта)
- ✅ `test_project_script_o3.py` - **СОХРАНЕН** (важный файл для проекта)
- ✅ `pydantic_settings/` - удален (неправильно установленная зависимость)
- ✅ `email_validator-2.0.0.dist-info/` - удален (неправильно установленная зависимость)
- ✅ `test.env` - удален (дублировал .env.example)

### Организованные скрипты:
```
scripts/
├── debug/          # 7 отладочных скриптов + run_debug.bat
├── test/           # 16 тестовых скриптов + run_tests.bat
├── services/       # 11 сервисных скриптов + run_services.bat
├── git/           # 8 git операций + cleanup_temp.bat
├── database/      # 3 скрипта БД + run_database.bat
└── run_scripts.bat # Главный меню
```

### Созданные bat файлы:
- `scripts/run_scripts.bat` - главное меню
- `scripts/debug/run_debug.bat` - отладочные скрипты
- `scripts/test/run_tests.bat` - тестовые скрипты
- `scripts/services/run_services.bat` - сервисные скрипты
- `scripts/database/run_database.bat` - скрипты БД
- `scripts/git/cleanup_temp.bat` - очистка временных файлов 