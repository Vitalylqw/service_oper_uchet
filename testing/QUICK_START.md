# 🚀 БЫСТРЫЙ СТАРТ ТЕСТИРОВАНИЯ

## 📋 ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

1. **Активированное виртуальное окружение Python**
   ```bash
   venv\Scripts\Activate.ps1
   ```

2. **Установленные зависимости**
   ```bash
   pip install -r requirements.txt
   ```

3. **База данных SQLite с тестовыми данными**
   - Файл: `data\service_oper_uchet.sqlite`

4. **Excel файл для тестирования**
   - Файл: `data\real_data_for_testing\Data_source_excel.xlsx`

## 🎯 БЫСТРЫЙ ЗАПУСК ВСЕХ ТЕСТОВ

```bash
# Запуск всех тестов одним кликом
testing\run_all_tests.bat
```

Этот скрипт автоматически:
- ✅ Активирует виртуальное окружение
- ✅ Запускает все тесты по порядку
- ✅ Запускает API сервер и React UI
- ✅ Показывает результаты

## 🔧 ИНДИВИДУАЛЬНЫЕ ТЕСТЫ

### 1. Тест базы данных
```bash
testing\test_database.bat
```

### 2. Тест парсинга Excel
```bash
testing\test_excel_parsing.bat
```

### 3. Тест синхронизации
```bash
testing\test_sync_integration.bat
```

### 4. Тест API сервера
```bash
testing\test_api_server.bat
```

### 5. Тест фронтенда
```bash
testing\test_frontend.bat
```

## 🌐 ЗАПУСК СЕРВЕРОВ

### API сервер
```bash
testing\start_api_server.bat
```
- Доступен по адресу: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

### React UI
```bash
testing\start_react_ui.bat
```
- Доступен по адресу: http://localhost:3000

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### ✅ Успешные тесты покажут:
- **База данных**: 30 сделок, 4 сессии, 213 событий
- **Excel парсинг**: 15 сделок, 84 позиции, 0 ошибок
- **Синхронизация**: 99 изменений, ~0.32 сек
- **API сервер**: Все endpoints работают
- **Фронтенд**: React UI доступен

### ⚠️ Возможные предупреждения:
- API сервер требует ручного запуска
- React UI может загружаться медленно

## 🔐 ТЕСТОВЫЕ УЧЕТНЫЕ ДАННЫЕ

Для тестирования API и фронтенда используйте:
- **viewer/password** - базовый доступ
- **analyst/password** - аналитик
- **admin/password** - администратор

## 📁 СТРУКТУРА ПАПКИ TESTING

```
testing/
├── README.md                    # Подробная документация
├── QUICK_START.md              # Этот файл
├── run_all_tests.bat           # Запуск всех тестов
├── test_*.bat                  # Индивидуальные тесты
├── start_*.bat                 # Запуск серверов
├── scripts/                    # Python скрипты
│   ├── test_db_connection.py
│   ├── test_excel_parsing.py
│   ├── test_sync_integration.py
│   ├── test_api_quick.py
│   └── test_frontend.py
└── reports/                    # Отчеты
    ├── PROJECT_TESTING_REPORT.md
    └── test_results.json
```

## 🚨 УСТРАНЕНИЕ ПРОБЛЕМ

### API сервер не запускается
```bash
# Проверить порт
netstat -an | findstr :8000

# Запустить вручную
python -m uvicorn src.presentation.api.main:app --host 127.0.0.1 --port 8000
```

### React UI не доступен
```bash
# Проверить порт
netstat -an | findstr :3000

# Перейти в папку и запустить
cd src\presentation\web
npm start
```

### Ошибки импорта
```bash
# Убедиться, что src в PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%\src
```

## 📞 ПОДДЕРЖКА

При возникновении проблем:
1. Проверьте логи тестов
2. Убедитесь, что все файлы существуют
3. Проверьте доступность портов
4. Обратитесь к подробной документации: `testing\README.md`

## 🎉 ГОТОВО!

После успешного прохождения всех тестов система готова к использованию!

**Основные URL:**
- 🌐 React UI: http://localhost:3000
- 🔌 API сервер: http://localhost:8000
- 📚 Swagger UI: http://localhost:8000/docs 