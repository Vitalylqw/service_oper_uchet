# Database Cleanup Tools

Набор инструментов для очистки базы данных SQLite проекта `service_oper_uchet`.

## Файлы

- `clear_database.py` - Основной Python скрипт
- `clear_database.bat` - Интерактивный запуск с меню (для CMD)
- `quick_clear_database.bat` - Быстрая очистка (для CMD)
- `README_DATABASE_CLEANUP.md` - Подробная документация

## Использование

### Рекомендуемый способ (PowerShell):
```powershell
# Интерактивный запуск
.\clear_database.ps1

# Быстрая очистка
.\quick_clear_database.ps1

# Прямой запуск Python скрипта
python database_cleanup\clear_database.py --stats-only
```

### Альтернативный способ (CMD):
```cmd
# Интерактивный запуск
clear_database.bat

# Быстрая очистка
quick_clear_database.bat
```

### Из директории `data/database_cleanup/`:
```bash
# Прямой запуск Python скрипта
python clear_database.py --stats-only
```

## Структура

```
data/
├── database_cleanup/           # Эта директория
│   ├── clear_database.py
│   ├── clear_database.bat
│   ├── quick_clear_database.bat
│   ├── README_DATABASE_CLEANUP.md
│   └── README.md               # Этот файл
├── clear_database.ps1          # PowerShell скрипт (рекомендуется)
├── quick_clear_database.ps1    # PowerShell скрипт (рекомендуется)
├── service_oper_uchet.sqlite   # База данных
├── backup/                     # Резервные копии
└── database_cleanup.log        # Лог файл
```

## Рекомендации

- **Для Windows PowerShell**: Используйте `.ps1` файлы
- **Для CMD**: Используйте `.bat` файлы
- **Для автоматизации**: Используйте прямой запуск Python скрипта

Подробная документация: `README_DATABASE_CLEANUP.md`