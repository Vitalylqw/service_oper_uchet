# Тестирование SERVICE_OPER_UCHET

## �� Запуск тестов

### Единственный способ
```bash
testing\run_tests.bat
```

Этот файл запускает все тесты по порядку:
1. Тестирование базы данных
2. Тестирование парсинга Excel
3. Тестирование синхронизации
4. Запуск и тестирование API сервера
5. Запуск и тестирование React UI

## 📁 Структура файлов

```
testing/
├── run_tests.bat              # ЕДИНСТВЕННЫЙ файл для запуска всех тестов
├── start_api_server.bat       # Запуск API сервера
├── start_react_ui.bat         # Запуск React UI
├── scripts/                   # Python скрипты тестирования
│   ├── test_db_connection.py
│   ├── test_excel_parsing.py
│   ├── test_sync_integration.py
│   ├── test_api_quick.py
│   └── test_frontend.py
└── reports/                   # Отчеты о тестировании
    ├── PROJECT_TESTING_REPORT.md
    └── test_results.json
```

## 🌐 Доступные сервисы

После успешного запуска тестов:
- **API сервер**: http://localhost:8000
- **React UI**: http://localhost:3000
- **Swagger UI**: http://localhost:8000/docs

## ⚠️ Требования

- Python 3.8+
- Установленные зависимости из `requirements.txt`
- База данных SQLite в папке `data/`

## 💡 Преимущества

- ✅ **Один файл** - нет путаницы с дубликатами
- ✅ **Простая структура** - легко понять и использовать
- ✅ **Правильная кодировка** - русский текст отображается корректно
- ✅ **Автоматический запуск** - все тесты выполняются последовательно 