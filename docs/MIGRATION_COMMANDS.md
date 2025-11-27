# Руководство по запуску миграций

## 🚀 Основные команды Alembic

### Переход в директорию миграций
```bash
cd migrations
```

## 📋 Проверка статуса

### 1. Текущая версия БД
```bash
alembic current
# Краткий вывод

alembic current -v
# Подробный вывод с описанием
```

### 2. История миграций
```bash
alembic history
# Список всех миграций

alembic history --verbose
# Подробная история с описаниями
```

### 3. Проверка соответствия схемы
```bash
alembic check
# Проверяет, есть ли различия между БД и моделями SQLAlchemy
```

## ⬆️ Применение миграций

### 1. Применить все миграции (до самой новой)
```bash
alembic upgrade head
```

### 2. Применить конкретную миграцию
```bash
alembic upgrade 0001
# Применить миграцию с ID 0001
```

### 3. Применить следующую миграцию
```bash
alembic upgrade +1
# Применить на одну версию вперед
```

### 4. Показать SQL без выполнения
```bash
alembic upgrade head --sql
# Покажет SQL код, который будет выполнен
```

## ⬇️ Откат миграций

### 1. Откат на одну версию назад
```bash
alembic downgrade -1
```

### 2. Откат к конкретной версии
```bash
alembic downgrade 0001
```

### 3. Полный откат (ВНИМАНИЕ: удаляет все данные!)
```bash
alembic downgrade base
```

### 4. Показать SQL отката без выполнения
```bash
alembic downgrade -1 --sql
```

## 🆕 Создание новых миграций

### 1. Автоматическая миграция на основе изменений моделей
```bash
alembic revision --autogenerate -m "Описание изменений"
```

### 2. Пустая миграция для ручных изменений
```bash
alembic revision -m "Описание изменений"
```

## 🔧 Дополнительные команды

### 1. Показать детали конкретной миграции
```bash
alembic show 0001
```

### 2. Принудительно установить версию без выполнения миграции
```bash
alembic stamp 0001
# ОСТОРОЖНО: используйте только если знаете что делаете!
```

### 3. Создать таблицу версий (если не существует)
```bash
alembic ensure_version
```

## 📝 Сценарии использования

### Сценарий 1: Новая чистая БД
```bash
cd migrations
alembic upgrade head
```

### Сценарий 2: Обновление существующей БД
```bash
cd migrations
alembic current          # Проверить текущую версию
alembic check            # Проверить, нужны ли обновления
alembic upgrade head     # Применить все новые миграции
```

### Сценарий 3: Проверка изменений без применения
```bash
cd migrations
alembic upgrade head --sql > migration_preview.sql
# Сохранить SQL в файл для проверки
```

### Сценарий 4: Разработка - создание новой миграции
```bash
cd migrations
alembic revision --autogenerate -m "Add new field to users"
# Создать миграцию на основе изменений в моделях

alembic upgrade head
# Применить новую миграцию
```

## 🚨 Важные примечания

### ⚠️ Безопасность
- **ВСЕГДА** делайте бэкап БД перед применением миграций в production
- **ТЕСТИРУЙТЕ** миграции на копии production данных
- **ПРОВЕРЯЙТЕ** SQL код миграции перед применением

### 🔍 Отладка
```bash
# Включить подробное логирование
alembic -q upgrade head    # Тихий режим
alembic --raiseerr upgrade head  # Показать полный stack trace при ошибках
```

### 📁 Конфигурация
```bash
# Использовать альтернативный конфиг
alembic -c custom_alembic.ini upgrade head

# Передать дополнительные параметры в env.py
alembic -x setting1=value1 upgrade head
```

## 🛠️ Наши скрипты

### Быстрое тестирование схемы
```bash
python scripts/test_new_schema.py
# Или
scripts/test_database_schema.bat  # Windows
```

### Исправление различий схемы (если нужно)
```bash
python scripts/fix_schema_differences.py
```

## 📖 Примеры для нашего проекта

### Полная настройка новой БД
```bash
# 1. Запустить PostgreSQL (если еще не запущен)
docker-compose -f docker-compose.db.yml up -d

# 2. Применить миграции
cd migrations
alembic upgrade head

# 3. Протестировать схему
cd ..
python scripts/test_new_schema.py
```

### Проверка состояния
```bash
cd migrations
alembic current -v        # Текущая версия: должна быть 0003 (или выше)
alembic check             # Должно быть: "No new upgrade operations detected"
```

### Доступные миграции

| Версия | Описание | Изменения |
|--------|----------|-----------|
| `0001` | Initial complete schema | Создание всех таблиц |
| `0002` | Add unique constraint | Уникальное ограничение для (deal_id, position_number) |
| `0003` | Change precision for purchase_price and margin | Изменение точности `purchase_price_amount` и `margin_amount` до 5 знаков (NUMERIC(18,5)) |

### При получении новых миграций из git
```bash
cd migrations
alembic history           # Посмотреть новые миграции
alembic upgrade head      # Применить все новые
```

---

**💡 Совет**: Добавьте псевдонимы в bash для удобства:
```bash
alias alem='cd /path/to/project/migrations'
alias alemup='cd /path/to/project/migrations && alembic upgrade head'
alias alemcur='cd /path/to/project/migrations && alembic current -v'
alias alemcheck='cd /path/to/project/migrations && alembic check'
```







