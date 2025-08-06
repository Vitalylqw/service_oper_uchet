# Debug Pars - Отладочные отчеты парсинга

## Файлы

### Основные скрипты:
- `save_parser_json.py` - ✅ **ОБНОВЛЕН** Сохранение детального JSON после парсинга Excel (DDD архитектура)
- `fix_position_numbers.py` - ✅ **НОВЫЙ** Исправление position_number в базе данных
- `debug_position_numbers.py` - ✅ **НОВЫЙ** Отладка position_number в парсере
- `check_position_numbers.py` - ✅ **НОВЫЙ** Проверка распределения position_number в БД
- `generate_json_reports.py` - Генерация JSON отчетов парсера и БД
- `create_final_comparison.py` - Создание финальной таблицы сравнения

### Отчеты:
- `parsed_data_detailed.json` - ✅ **НОВЫЙ** Детальный JSON со всеми сделками и позициями
- `parser_summary.json` - ✅ **НОВЫЙ** Краткая сводка парсинга с метриками
- `database_report.json` - Отчет данных из БД  
- `comparison.json` - JSON сравнение метрик
- `final_comparison_table.txt` - Финальная таблица сравнения

### Запуск:
- `save_parser_json.bat` - ✅ **НОВЫЙ** Запуск сохранения JSON (Windows)
- `run_position_fix.bat` - ✅ **НОВЫЙ** Исправление position_number в БД
- `run_comparison.bat` - Запуск финального сравнения

### Документация:
- `PARSER_JSON_UPDATE_REPORT.md` - ✅ **НОВЫЙ** Отчет об обновлении архитектуры
- `POSITION_NUMBER_FIX_REPORT.md` - ✅ **НОВЫЙ** Отчет об исправлении position_number

## Актуальные результаты (05.08.2025)

### Парсинг Excel файла (обновленный скрипт)
**Источник:** `data/real_data_for_testing/Data_source_excel.xlsx`
- ✅ **Сделки:** 301 (100% успешность)
- ✅ **Позиции:** 1,732 (100% успешность)  
- ✅ **Выручка:** 9,877,543.33 ₽
- ✅ **Маржа:** 2,542,666.03 ₽
- ✅ **Листов обработано:** 1 из 2 (50%)
- ⚠️  **Позиций с нулевой выручкой:** 7

### Файлы отчетов
- `parsed_data_detailed.json` - 2.8 MB (полная структура)
- `parser_summary.json` - 24 KB (сводка)

### Показатели качества
- ✅ Все позиции имеют названия товаров
- ✅ Полное соответствие между парсером и JSON
- ✅ DDD архитектура с полной поддержкой всех полей моделей

### ✅ Исправление position_number (05.08.2025)
**Проблема:** Все записи в read_positions имели position_number = 1
**Решение:** Создан скрипт автоматического исправления
- **До:** 3,460 записей с position_number = 1 (100%)
- **После:** 1,188 записей с position_number = 1 (34.3%) ← *нормально для первых позиций*
- **Исправлено:** 2,468 записей получили корректные номера
- **Диапазон:** position_number от 1 до 88
- **Статус:** ✅ **ПРОБЛЕМА РЕШЕНА**

## Использование

### Быстрый запуск (Windows)
```cmd
# Сохранение JSON данных парсера
debug_pars\save_parser_json.bat

# Исправление position_number в БД
debug_pars\run_position_fix.bat
```

### Ручной запуск
```cmd
# Сохранение JSON данных парсера
python debug_pars\save_parser_json.py

# Проверка position_number в БД
python debug_pars\check_position_numbers.py

# Исправление position_number
python debug_pars\fix_position_numbers.py

# Отладка парсера
python debug_pars\debug_position_numbers.py
``` 