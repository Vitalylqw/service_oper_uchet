# Scripts Directory

Организованная коллекция скриптов для разработки и обслуживания проекта.

## Структура

```
scripts/
├── debug/          # Отладочные скрипты (7 файлов)
├── test/           # Тестовые скрипты (16 файлов)
├── services/       # Сервисные скрипты (11 файлов)
├── git/           # Git операции (8 файлов)
├── database/      # Работа с БД (3 файла)
└── run_scripts.bat # Главное меню
```

## Использование

### Быстрый запуск
```bash
scripts/run_scripts.bat
```

### Категорийные меню
- `debug/run_debug.bat` - отладочные скрипты
- `test/run_tests.bat` - тестовые скрипты
- `services/run_services.bat` - сервисные скрипты
- `database/run_database.bat` - скрипты БД

### Git операции
- `git/cleanup_temp.bat` - очистка временных файлов
- `git/push_to_github.bat` - отправка в GitHub
- `git/add_and_commit.bat` - добавление и коммит

## Категории

### Debug (7 файлов)
Отладочные скрипты для диагностики проблем:
- `debug_deal_endpoint.py` - отладка endpoint сделок
- `debug_auth.py` - отладка аутентификации
- `debug_database_stats.py` - статистика БД
- `debug_api_deals.py` - отладка API сделок
- `debug_events.py` - отладка событий
- `debug_db_tables.py` - отладка таблиц БД

### Test (16 файлов)
Тестовые скрипты для проверки функциональности:
- `test_specific_deal.py` - тест конкретной сделки
- `test_jwt.py` - тест JWT токенов
- `test_excel_parsing.py` - тест парсинга Excel
- `test_frontend.py` - тест фронтенда
- `test_sync_integration.py` - тест синхронизации
- И другие...

### Services (11 файлов)
Сервисные скрипты для обслуживания:
- `check_data.py` - проверка данных
- `check_swagger.py` - проверка Swagger
- `fix_read_model_builder.py` - исправление read model builder
- `build_read_models.py` - сборка read models
- `final_check.py` - финальная проверка
- `run_sync_once.py` - однократная синхронизация
- И другие...

### Git (8 файлов)
Операции с Git:
- `push_to_github.bat` - отправка в GitHub
- `simple_push.bat` - простая отправка
- `check_last_commit.bat` - проверка последнего коммита
- `add_and_commit.bat` - добавление и коммит
- `check_git_status.bat` - статус Git
- `cleanup_temp.bat` - очистка временных файлов

### Database (3 файла)
Работа с базой данных:
- `create_sample_excel.py` - создание образца Excel
- `init_database.py` - инициализация БД
- `create_schema.py` - создание схемы

## Рекомендации

1. **Запуск**: Всегда используйте `run_scripts.bat` для запуска
2. **Добавление**: Новые скрипты размещайте в соответствующих папках
3. **Обновление**: При добавлении скриптов обновляйте bat файлы
4. **Очистка**: Регулярно используйте `git/cleanup_temp.bat` 