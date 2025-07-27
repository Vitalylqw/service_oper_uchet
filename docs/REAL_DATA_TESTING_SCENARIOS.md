# Сценарии тестирования полного цикла с реальными данными

> **Цель**: Протестировать весь пайплайн от Excel файла до UI  
> **Источник данных**: `data/excel/Data_source_excel.xlsx` и `Data_source_excel.xlsx`  
> **База данных**: `data/service_oper_uchet.sqlite`  
> **Серверы**: `start_api_server.bat` + `start_react_ui.bat`

## 🎯 Основные сценарии

### Сценарий 1: Базовый полный цикл

```python
def test_basic_full_cycle():
    """
    Базовый тест полного цикла Excel → API → БД → UI.
    
    Шаги:
    1. Запуск API сервера (start_api_server.bat)
    2. Запуск React UI (start_react_ui.bat)  
    3. Загрузка Excel через API
    4. Проверка данных в БД
    5. Проверка отображения в UI
    """
    
    # 1. Проверка серверов
    assert check_api_server("http://localhost:8000")
    assert check_ui_server("http://localhost:3000")
    
    # 2. Загрузка Excel файла
    excel_file = "Data_source_excel.xlsx"
    session_result = create_sync_session(excel_file)
    assert session_result["status"] == "success"
    
    # 3. Проверка в БД
    db_data = check_database_data()
    assert db_data["deals_count"] > 0
    assert db_data["items_count"] > 0
    
    # 4. Проверка UI доступности
    ui_status = check_ui_accessibility()
    assert ui_status["main_page_loads"] == True
    
    return {
        "deals_processed": db_data["deals_count"],
        "items_processed": db_data["items_count"],
        "ui_accessible": True
    }
```

### Сценарий 2: Производительность с реальными данными

```python
def test_performance_with_real_data():
    """
    Тест производительности обработки реального Excel файла.
    
    Метрики:
    - Время обработки < 30 сек
    - Память < 100MB
    - API ответы < 1 сек
    """
    import time
    import psutil
    
    start_time = time.time()
    memory_start = get_memory_usage()
    
    # Обработка файла
    result = process_excel_file("Data_source_excel.xlsx")
    
    processing_time = time.time() - start_time
    memory_used = get_memory_usage() - memory_start
    
    # Проверка производительности
    assert processing_time < 30.0, f"Слишком долго: {processing_time:.2f}с"
    assert memory_used < 100.0, f"Много памяти: {memory_used:.2f}MB"
    
    # Проверка API
    api_response_time = measure_api_response_time()
    assert api_response_time < 1.0, f"API медленный: {api_response_time:.2f}с"
    
    return {
        "processing_time": processing_time,
        "memory_used": memory_used,
        "api_response_time": api_response_time,
        "grade": "A" if processing_time < 10 else "B"
    }
```

### Сценарий 3: Проверка данных

```python
def test_data_validation_full_cycle():
    """
    Тест валидации данных в полном цикле.
    
    Проверяет:
    - Корректность парсинга Excel
    - Сохранение в БД без потерь
    - Консистентность API ответов
    """
    
    # 1. Парсинг Excel
    excel_data = parse_excel_file("Data_source_excel.xlsx")
    original_deals = len(excel_data["deals"])
    original_items = len(excel_data["items"])
    
    # 2. Обработка через API
    session = create_sync_session("Data_source_excel.xlsx")
    
    # 3. Проверка в БД
    db_deals = get_deals_from_db()
    db_items = get_items_from_db()
    
    # 4. Проверка через API
    api_deals = get_deals_from_api()
    
    # Валидация консистентности
    assert len(db_deals) == original_deals, "Потеря данных сделок в БД"
    assert len(db_items) == original_items, "Потеря данных товаров в БД"
    assert len(api_deals) == len(db_deals), "Несоответствие API и БД"
    
    # Проверка структуры данных
    for deal in api_deals:
        assert "id" in deal
        assert "client_name" in deal
        assert "invoice_info" in deal
        assert deal["period"] is not None
    
    return {
        "original_deals": original_deals,
        "db_deals": len(db_deals),
        "api_deals": len(api_deals),
        "data_integrity": "OK"
    }
```

## 🛠️ Вспомогательные функции

### Проверка серверов

```python
def check_api_server(url: str) -> bool:
    """Проверка доступности API сервера."""
    try:
        import requests
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_ui_server(url: str) -> bool:
    """Проверка доступности UI сервера."""
    try:
        import requests
        response = requests.get(url, timeout=5)
        return response.status_code == 200 and "text/html" in response.headers.get("content-type", "")
    except:
        return False
```

### Работа с данными

```python
def create_sync_session(file_path: str) -> dict:
    """Создание sync session через API."""
    import requests
    
    # Получение токена аналитика
    token = get_analyst_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "file_path": file_path,
        "session_type": "full"
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/sessions/",
        json=payload,
        headers=headers
    )
    
    if response.status_code in [200, 201]:
        return {
            "status": "success",
            "session_id": response.json()["id"]
        }
    else:
        return {
            "status": "error",
            "error": response.text
        }

def check_database_data() -> dict:
    """Проверка данных в SQLite БД."""
    import sqlite3
    
    conn = sqlite3.connect("data/service_oper_uchet.sqlite")
    cursor = conn.cursor()
    
    # Подсчет сделок
    cursor.execute("SELECT COUNT(*) FROM deal_read_model")
    deals_count = cursor.fetchone()[0]
    
    # Подсчет товаров (если есть таблица)
    try:
        cursor.execute("SELECT COUNT(*) FROM deal_item_read_model")
        items_count = cursor.fetchone()[0]
    except:
        items_count = 0
    
    conn.close()
    
    return {
        "deals_count": deals_count,
        "items_count": items_count
    }

def get_deals_from_api() -> list:
    """Получение сделок через API."""
    import requests
    
    token = get_viewer_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        "http://localhost:8000/api/v1/deals",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()["items"]
    else:
        return []
```

### Метрики производительности

```python
def get_memory_usage() -> float:
    """Получение использования памяти в MB."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def measure_api_response_time() -> float:
    """Измерение времени ответа API."""
    import requests
    import time
    
    token = get_viewer_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    
    response = requests.get(
        "http://localhost:8000/api/v1/deals",
        headers=headers
    )
    
    response_time = time.time() - start_time
    
    return response_time if response.status_code == 200 else 999.0
```

## 📋 Чек-лист перед тестированием

### Подготовка окружения

- [ ] ✅ Виртуальное окружение активировано
- [ ] ✅ Все зависимости установлены (`pip install -r requirements.txt`)
- [ ] ✅ Excel файл `Data_source_excel.xlsx` существует
- [ ] ✅ База данных `data/service_oper_uchet.sqlite` доступна (или будет создана)

### Запуск серверов

- [ ] ✅ API сервер запущен: `start_api_server.bat`
  - Проверка: http://localhost:8000/health
- [ ] ✅ React UI запущен: `start_react_ui.bat`  
  - Проверка: http://localhost:3000

### Проверка API

- [ ] ✅ Health endpoint отвечает: `/health`
- [ ] ✅ Аутентификация работает: `/api/v1/auth/*`
- [ ] ✅ Deals endpoint доступен: `/api/v1/deals`
- [ ] ✅ Sessions endpoint доступен: `/api/v1/sessions`

## 🎮 Команды запуска

### Быстрый тест полного цикла

```bash
# Предполагает, что серверы уже запущены
python -m pytest tests/e2e/ -k "full_cycle" -v
```

### Тест с подробным выводом

```bash
# С детальной информацией
python -m pytest tests/e2e/ -v --tb=long -s
```

### Тест производительности

```bash
# Только тесты производительности
python -m pytest tests/e2e/ -k "performance" -v
```

### Полный набор E2E тестов

```bash
# Все E2E тесты включая существующие
python -m pytest -m "e2e" -v
```

## 📊 Ожидаемые результаты

### С файлом Data_source_excel.xlsx (19KB)

```
📈 ОЖИДАЕМЫЕ МЕТРИКИ:

Размер файла: 19KB
Строки данных: ~100
Ожидаемые сделки: 15-30
Ожидаемые товары: 50-150

Время обработки: 5-20 секунд
Использование памяти: 20-50MB
Размер БД после обработки: 100-300KB

API производительность:
- GET /api/v1/deals: < 1 сек
- POST /api/v1/sessions: < 20 сек
- GET /health: < 0.1 сек

UI доступность:
- Загрузка главной страницы: < 2 сек
- Отображение списка сделок: < 3 сек
```

### Критерии успешности

| Компонент | Критерий | Допустимое время |
|-----------|----------|------------------|
| **Excel парсинг** | Без ошибок, все данные извлечены | < 30 сек |
| **API обработка** | HTTP 200/201, данные сохранены | < 30 сек |
| **База данных** | Все записи сохранены | < 10 сек |
| **UI загрузка** | Страница отображается | < 5 сек |
| **Общий цикл** | Данные доступны через все интерфейсы | < 60 сек |

---

**📅 Создано:** 24 января 2025  
**🎯 Назначение:** Практическое руководство по тестированию полного цикла  
**🔄 Обновления:** После изменений в API или структуре данных 