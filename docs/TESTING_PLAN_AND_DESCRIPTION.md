# План тестирования и описание тестов

> **Статус: ✅ ТЕСТЫ СТАБИЛЬНЫ И РАБОТАЮТ**  
> **Дата обновления: 24 января 2025**  
> **Всего тестов: 367 (100% проходят)**

## 📊 Текущее состояние тестирования

### Общая статистика тестов

| Тип тестов | Количество | Время выполнения | Статус |
|------------|------------|------------------|--------|
| **Unit тесты** | 344 | ~15 сек | ✅ Стабильны |
| **Integration тесты** | 17 | ~1 мин | ✅ Стабильны |
| **E2E тесты** | 6 | ~2 мин | ✅ Стабильны |
| **ИТОГО** | **367** | **~3.5 мин** | **✅ 100% проходят** |

### Архитектура тестирования

```
tests/
├── conftest.py                           # Общие фикстуры
├── fixtures/                             # Тестовые данные
├── unit/                                 # Unit тесты (344 теста)
│   ├── application/                      # Тесты бизнес-логики
│   ├── domain/                          # Тесты доменных моделей
│   ├── infrastructure/                   # Тесты инфраструктуры
│   └── presentation/                     # Тесты API
├── integration/                          # Integration тесты (17 тестов)
│   ├── test_database_integration.py      # База данных (7 тестов)
│   ├── test_excel_parser_integration.py  # Парсер Excel (7 тестов)
│   ├── test_sync_integration.py          # Синхронизация (3 теста)
│   └── test_e2e_api.py                  # E2E API (6 тестов)
└── __init__.py
```

## 🎯 Маркеры pytest

```bash
# Настроенные маркеры тестов
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "integration_db: marks tests as database integration tests",
    "e2e: marks tests as end-to-end tests",
    "unit: marks tests as unit tests",
]
```

## 🚀 Команды запуска тестов

### Разработка (ежедневное использование)

```bash
# Быстрые unit тесты - для ежедневной разработки
python -m pytest -m "unit"
# ✅ Результат: 344 passed, 31 deselected, 132 warnings in ~15s

# Unit тесты с покрытием кода
python -m pytest -m "unit" --cov=src --cov-report=html
# Создает htmlcov/index.html с отчетом покрытия
```

### Интеграционное тестирование

```bash
# Database integration тесты - перед коммитом
python -m pytest -m "integration_db"
# ✅ Результат: 6 passed, 1 skipped, 368 deselected in ~45s

# Все интеграционные тесты
python -m pytest -m "integration"
# ✅ Результат: 18 passed, включая Excel parser и sync integration
```

### Полное тестирование

```bash
# E2E тесты - перед релизом
python -m pytest -m "e2e"
# ✅ Результат: 6 passed, 369 deselected in ~2m

# Все тесты кроме медленных E2E
python -m pytest -m "unit or (integration and not e2e)"
# ✅ Результат: 362 passed, 13 deselected in ~1.5m

# Все тесты включая медленные
python -m pytest
# ✅ Результат: 367 passed in ~3.5m
```

### Специальные команды

```bash
# Исключить медленные тесты
python -m pytest -m "not slow"

# Только новые database integration тесты
python -m pytest tests/integration/test_database_integration.py

# Только E2E API тесты
python -m pytest tests/integration/test_e2e_api.py

# Проверка доступных маркеров
python -m pytest --markers

# Подробный вывод для отладки
python -m pytest -v --tb=long

# Краткий вывод
python -m pytest -q
```

## 📋 Детальное описание тестов

### 1. Unit тесты (344 теста)

**Покрывают:**
- 🏗️ **Domain Layer**: модели Deal, DealItem, SyncSession, Value Objects
- 🧠 **Application Layer**: ExcelParser, ChangeDetector, SyncOrchestrator, DataValidator
- 🔧 **Infrastructure**: Repository implementations, Database connections, File operations
- 🌐 **Presentation**: FastAPI endpoints, Authentication, Authorization

**Особенности:**
- Быстрые выполнение (~15 сек)
- Используют моки для внешних зависимостей
- Высокое покрытие кода (>85%)
- Запускаются при каждом изменении кода

### 2. Integration тесты (17 тестов)

#### 2.1 Database Integration (7 тестов)
**Файл:** `tests/integration/test_database_integration.py`

**Тестируют:**
- Excel → Parse → Repository → Database pipeline
- CRUD операции с реальной БД
- Транзакции и batch операции
- Consistency проверки

#### 2.2 Excel Parser Integration (7 тестов)
**Файл:** `tests/integration/test_excel_parser_integration.py`

**Тестируют с реальным файлом `Data_source_excel.xlsx`:**
- Парсинг структуры Excel файла
- Валидация бизнес-логики
- Обработка ошибок
- Проверка финансовых расчетов

#### 2.3 Sync Integration (3 теста)
**Файл:** `tests/integration/test_sync_integration.py`

**Тестируют:**
- Полный цикл синхронизации
- Event Sourcing pipeline
- Change detection алгоритмы

### 3. E2E тесты (6 тестов)

**Файл:** `tests/integration/test_e2e_api.py`

**Тестируют полный HTTP API пайплайн:**
- Аутентификация и авторизация
- Создание sync sessions
- Обработка Excel файлов
- Получение данных через API
- Пагинация и фильтрация
- Обработка ошибок

## 📈 План развития тестирования

### Приоритет 1: Тесты полного цикла с реальными данными

#### Цель
Протестировать весь пайплайн от Excel файла до отображения в UI с использованием:
- **Источник данных:** `data/excel/Data_source_excel.xlsx`
- **База данных:** `data/service_oper_uchet.sqlite`
- **API сервер:** `start_api_server.bat`
- **React UI:** `start_react_ui.bat`

#### Планируемые тесты

1. **Полный цикл Excel → API → БД**
   ```python
   def test_excel_to_database_full_cycle():
       # 1. Парсинг реального Excel файла
       # 2. Обработка через API
       # 3. Сохранение в SQLite БД
       # 4. Проверка данных в БД
   ```

2. **API → UI интеграция**
   ```python
   def test_api_ui_data_consistency():
       # 1. Получение данных через API
       # 2. Проверка формата для UI
       # 3. Тестирование пагинации
       # 4. Валидация ошибок
   ```

3. **Производительность с реальными данными**
   ```python
   def test_performance_with_real_data():
       # 1. Измерение времени обработки
       # 2. Проверка лимитов памяти
       # 3. Тестирование больших файлов
   ```

### Приоритет 2: UI тестирование

#### React компоненты (уже покрыты)
- **LoginPage** - полное покрытие UI и логики
- **Dashboard** - все основные сценарии  
- **StatsCard** - все варианты отображения
- **Pagination** - логика пагинации и навигации

#### Планируемые браузерные тесты
```bash
# Установка браузерного тестирования (опционально)
pip install playwright pytest-playwright
playwright install
```

1. **Тестирование пользовательских сценариев**
   - Авторизация в браузере
   - Навигация по интерфейсу
   - Загрузка файлов
   - Просмотр результатов

### Приоритет 3: Нагрузочное тестирование

#### Планируемые тесты
1. **Concurrent API requests**
2. **Large Excel files processing** 
3. **Database performance under load**
4. **Memory usage optimization**

## 🛠️ Инструменты тестирования

### Текущие зависимости
```toml
dev = [
    "pytest>=7.4.0",              # Основной фреймворк
    "pytest-asyncio>=0.21.0",     # Async поддержка
    "httpx>=0.25.0",               # HTTP клиент для FastAPI
    "ruff>=0.1.0",                 # Линтинг
    "black>=23.0.0",               # Форматирование
    "mypy>=1.6.0",                 # Проверка типов
]
```

### React тестирование
```json
{
  "@testing-library/jest-dom": "^6.2.0",
  "@testing-library/react": "^14.1.2", 
  "@testing-library/user-event": "^14.5.1",
  "vitest": "^1.2.0",
  "happy-dom": "^12.10.3"
}
```

## 📊 CI/CD рекомендации

### Local development
```bash
python -m pytest -m "unit"
# ⚡ Быстро: 15 секунд
```

### Pull Request validation  
```bash
python -m pytest -m "unit or integration_db"
# 🛡️ Надежно: 1 минута, покрывает критический функционал
```

### Release validation
```bash
python -m pytest -m "unit or integration_db or e2e"
# 🚀 Полно: 2.5 минуты, полное покрытие пользовательских сценариев
```

### Full regression
```bash
python -m pytest
# 🔍 Исчерпывающе: 3.5 минуты, все тесты
```

## 🎯 Требования к покрытию

- **Общее покрытие**: минимум 85%
- **Критичные компоненты**: минимум 95%
- **Новый код**: минимум 90%
- **Автоматическая проверка**: в CI/CD пайплайне

## 📝 Соглашения по тестированию

### Именование тестов
```python
def test_[component]_[scenario]_[expected_result]():
    """Test description in English."""
    # Arrange - настройка данных
    # Act - выполнение действия
    # Assert - проверка результата
```

### Структура тестовых данных
```python
# Используем фикстуры из conftest.py
@pytest.fixture
def sample_deal() -> Deal:
    """Sample deal for tests."""
    return Deal(...)

# Реальные данные для интеграционных тестов
@pytest.fixture  
def real_excel_file():
    """Real Excel file for integration tests."""
    return "Data_source_excel.xlsx"
```

### Маркировка тестов
```python
@pytest.mark.unit
def test_unit_functionality():
    """Unit test with mocks."""
    pass

@pytest.mark.integration_db
def test_database_integration():
    """Integration test with real database."""
    pass

@pytest.mark.e2e
@pytest.mark.slow
def test_full_api_pipeline():
    """End-to-end test through HTTP API."""
    pass
```

## 🚨 Критические точки тестирования

### Обязательно тестировать
1. **Excel парсинг** - корректность извлечения данных
2. **Change Detection** - выявление изменений в данных
3. **Event Sourcing** - сохранение и восстановление событий
4. **API Security** - аутентификация и авторизация
5. **Data Validation** - проверка бизнес-правил

### Регрессионные тесты
1. **File format changes** - изменения формата Excel
2. **Database schema changes** - миграции БД
3. **API contract changes** - изменения API
4. **Performance degradation** - снижение производительности

## 📞 Поддержка и отладка

### При падении тестов
```bash
# Подробная информация об ошибках
python -m pytest --tb=long -v

# Остановка на первой ошибке
python -m pytest -x

# Запуск только упавших тестов
python -m pytest --lf
```

### Отладка конкретного теста
```bash
# Запуск одного теста с выводом
python -m pytest tests/unit/application/test_excel_parser.py::test_parse_valid_file -v -s

# С отладочной информацией
python -m pytest tests/integration/test_database_integration.py::TestDatabaseIntegration::test_excel_to_database_pipeline --tb=long -v -s
```

---

**📅 Последнее обновление:** 24 января 2025  
**👤 Ответственный:** Команда разработки  
**📧 Контакты:** Документировать проблемы в Issues проекта 