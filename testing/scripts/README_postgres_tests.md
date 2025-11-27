# PostgreSQL Integration Tests

Этот набор скриптов предназначен для тестирования синхронизации с использованием PostgreSQL.

## Предварительные требования

1. **PostgreSQL сервер** должен быть запущен (через docker-compose.db.yml)
2. **Python** с установленными зависимостями
3. **Файл config.env** с настройками PostgreSQL

## Запуск PostgreSQL

```bash
# Создать сеть Docker (если не существует)
docker network create devnet

# Запустить PostgreSQL
docker-compose -f docker-compose.db.yml up -d

# Проверить статус
docker-compose -f docker-compose.db.yml ps
```

## Файлы тестирования

### Основной скрипт
- `test_sync_integration.py` - основной скрипт тестирования

### Bat-файлы для Windows
- `test_sync_integration_postgres.bat` - базовый тест
- `test_sync_integration_interactive.bat` - интерактивный режим
- `test_sync_integration_debug.bat` - тест с отладочными логами

## Использование

### Командная строка
```bash
# Полная синхронизация (по умолчанию)
python test_sync_integration.py

# Инкрементальная синхронизация за 6 месяцев
python test_sync_integration.py --sync-type incremental --period-months 6

# С отладочными логами
python test_sync_integration.py --log-level DEBUG

# Интерактивный режим
python test_sync_integration.py --interactive
```

### Windows (bat-файлы)
```cmd
# Базовый тест
test_sync_integration_postgres.bat

# Интерактивный режим
test_sync_integration_interactive.bat

# С отладкой
test_sync_integration_debug.bat

# С параметрами
test_sync_integration_postgres.bat --sync-type incremental --period-months 6
```

## Конфигурация

Скрипт автоматически загружает настройки PostgreSQL из `config.env`:

```env
DB_TYPE=postgresql
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
```

## Что тестируется

1. **Подключение к PostgreSQL** - проверка соединения с БД
2. **Синхронизация данных** - полная или инкрементальная
3. **Верификация данных** - проверка результатов синхронизации
4. **Логирование** - детальные логи процесса

## Устранение неполадок

### Ошибка подключения к БД
- Убедитесь, что PostgreSQL запущен: `docker-compose -f docker-compose.db.yml ps`
- Проверьте настройки в `config.env`
- Проверьте доступность порта 5432

### Ошибка импорта модулей
- Убедитесь, что вы находитесь в корневой папке проекта
- Проверьте, что все зависимости установлены: `pip install -r requirements.txt`

### Ошибка Excel файла
- Убедитесь, что файл `data/real_data_for_testing/Data_source_excel.xlsx` существует
- Проверьте права доступа к файлу

## Логи

Тест создает детальные логи с указанием:
- Времени выполнения
- Уровня логирования
- Имени модуля, функции и строки
- Сообщений об ошибках

Уровни логирования:
- `INFO` - основная информация
- `DEBUG` - детальные логи для отладки




