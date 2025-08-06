# 🗄️ Управление базой данных

## 🆕 Создание новой базы данных

Если вы удалили файл базы данных или хотите создать новую с нуля:

### ⚡ Быстрый способ
```bash
# Запустить bat файл (Windows)
scripts/database/create_new_database.bat

# Или Python скрипт напрямую
python scripts/database/create_new_database.py
```

### 🔧 Ручной способ
```bash
# 1. Создать базовую схему
python scripts/database/init_database.py

# 2. Применить структурные изменения (если нужно)
python scripts/database/migrations/20250120_restructure_positions.py

# 3. Проверить статус
python scripts/database/check_database_status.py
```

## 📁 Структура новой базы данных

После создания у вас будет:

### Таблицы Event Store:
- `event_store` - хранение всех событий системы

### Read Models (оптимизированные представления):
- `read_deals` - сделки для быстрых запросов
- `read_positions` - позиции товаров (**с новой структурой**)
- `read_audit` - аудит изменений

### 🆕 Новая структура `read_positions`:
```sql
- id (UUID)
- deal_id (UUID) 
- deal_key (VARCHAR)
- position_number (INTEGER) ← НОВОЕ ПОЛЕ
- hash_key (VARCHAR) ← Теперь включает deal_key + position_number
- product_name (VARCHAR)
- supplier_name (VARCHAR)
- pickup_date (VARCHAR)
- quantity, prices, amounts...
- client_name, period_month, period_year
- system fields (created_at, updated_at, version)
```

### ❌ Удаленные поля:
- `position_key` - больше не используется

## 🔍 Проверка базы данных

```bash
# Проверить статус и структуру
python scripts/database/check_database_status.py

# Анализ структуры таблиц  
python scripts/database/analyze_database_structure.py
```

## 🗑️ Сброс базы данных

```bash
# Полный сброс (удаление и пересоздание)
scripts/database/reset_database.bat
```

## 📊 Файл базы данных

- **Путь**: `data/service_oper_uchet.sqlite`
- **Тип**: SQLite (для разработки)
- **Размер**: зависит от количества данных

## ⚠️ Важно!

После создания новой базы данных:

1. **Первая синхронизация** займет больше времени (нет кэша)
2. **Новая логика hash_key** - изменение порядка позиций в Excel считается изменением
3. **position_number** автоматически присваивается при парсинге (1, 2, 3...)

## 🚀 Готовность к работе

База данных готова когда:
- ✅ Все таблицы созданы
- ✅ Структура `read_positions` обновлена
- ✅ Тестовое подключение работает
- ✅ position_key удален, position_number добавлен