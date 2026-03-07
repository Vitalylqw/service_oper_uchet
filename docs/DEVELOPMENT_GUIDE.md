# 👨‍💻 РУКОВОДСТВО РАЗРАБОТЧИКА SERVICE_OPER_UCHET

> **Версия**: 1.0  
> **Дата обновления**: 27 января 2025  
> **Для**: Разработчики, DevOps, архитекторы

---

## 🎯 ОБЗОР АРХИТЕКТУРЫ

### Технический стек

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Database** | PostgreSQL/SQLite | 16+/3.35+ | Хранение данных |
| **Testing** | pytest | 7.4+ | Тестирование |
| **Linting** | Ruff | 0.1+ | Анализ кода |
| **Architecture** | DDD + Event Sourcing | - | Архитектурные паттерны |

### Архитектурные слои

```
src/
├── domain/              # Бизнес-логика
│   ├── models/          # Доменные сущности
│   ├── value_objects/   # Объекты-значения
│   ├── exceptions/      # Доменные исключения
│   └── interfaces/      # Интерфейсы репозиториев
├── application/         # Сценарии использования
│   ├── excel_parser/    # Парсинг Excel
│   ├── change_detector/ # Обнаружение изменений
│   ├── sync_orchestrator/ # Управление синхронизацией
│   └── data_validator/  # Валидация данных
├── infrastructure/      # Внешние сервисы
│   ├── database/        # БД и репозитории
│   ├── file_system/     # Работа с файлами
│   ├── scheduler/       # Планировщик задач
│   └── workers/         # Фоновые воркеры
```

---

## 🚀 НАСТРОЙКА ОКРУЖЕНИЯ РАЗРАБОТКИ

### Предварительные требования

```bash
# Python 3.9+
python --version

# Git
git --version

# PostgreSQL (опционально для разработки)
psql --version
```

### Установка зависимостей

#### Backend (Python)

```bash
# Клонирование репозитория
git clone https://github.com/Vitalylqw/service_oper_uchet.git
cd service_oper_uchet

# Создание виртуального окружения
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/macOS)
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Установка dev зависимостей
pip install -e ".[dev]"
```

### Конфигурация

#### Создание .env файла

```bash
# Скопируйте пример конфигурации
cp .env.example .env
```

#### Настройка .env

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=service_oper_uchet_dev
DB_USER=postgres
DB_PASSWORD=your_password

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True

# JWT Settings
SECRET_KEY=your-secret-key-for-development
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Settings
UPLOAD_DIR=data/uploads
MAX_FILE_SIZE=52428800

# Development Settings
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Запуск тестов

#### Все тесты

```bash
# Запуск всех тестов
python -m pytest

# С подробным выводом
python -m pytest -v

# С покрытием
python -m pytest --cov=src --cov-report=html
```

#### Типы тестов

```bash
# Unit тесты (быстро)
python -m pytest -m "unit"

# Integration тесты
python -m pytest -m "integration"

# Database integration тесты
python -m pytest -m "integration_db"

# E2E тесты
python -m pytest -m "e2e"

# Медленные тесты
python -m pytest -m "slow"
```

### Написание тестов

#### Unit тесты (Python)

```python
import pytest
from src.domain.models import Deal
from src.application.excel_parser.parser import ExcelParserService

class TestExcelParserService:
    @pytest.mark.asyncio
    async def test_parse_excel_file(self, excel_file_fixture):
        # Arrange
        parser = ExcelParserService()
        
        # Act
        result = await parser.parse_file(excel_file_fixture)
        
        # Assert
        assert len(result.deals) > 0
        assert all(isinstance(deal, Deal) for deal in result.deals)
```

#### Integration тесты

```python
import pytest
from src.infrastructure.database.connection import _db_manager

class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_deal_repository_crud(self, test_database):
        # Arrange
        async with _db_manager.get_async_session() as session:
            repository = DealRepository(session)
            
            # Act
            deal = Deal(
                deal_id="TEST-001",
                client_name="Test Client",
                invoice_number="INV-001"
            )
            await repository.create(deal)
            
            # Assert
            retrieved = await repository.get_by_id("TEST-001")
            assert retrieved.client_name == "Test Client"
```

---

## 🔧 РАЗРАБОТКА

### Стандарты кода

#### Python (PEP8 + дополнительные правила)

```python
# ✅ Правильно
from typing import List, Optional
from src.domain.models import Deal
from src.application.excel_parser.parser import ExcelParserService

class DealService:
    """Сервис для работы со сделками."""
    
    def __init__(self, parser: ExcelParserService) -> None:
        self.parser = parser
    
    async def process_excel_file(self, file_path: str) -> List[Deal]:
        """Обрабатывает Excel файл и возвращает список сделок."""
        return await self.parser.parse_file(file_path)
```

### Линтинг и форматирование

#### Backend

```bash
# Проверка кода
ruff check .

# Автоматическое исправление
ruff check --fix .

# Форматирование
black .

# Проверка типов
mypy src/
```

### Git workflow

#### Conventional Commits

```bash
# Новые функции
git commit -m "feat: add Excel file validation"

# Исправления ошибок
git commit -m "fix: resolve date parsing issue"

# Документация
git commit -m "docs: update API documentation"

# Тесты
git commit -m "test: add unit tests for validation"

# Рефакторинг
git commit -m "refactor: improve error handling"
```

#### Feature branches

```bash
# Создание feature branch
git checkout -b feature/excel-validation

# Разработка
# ... код ...

# Коммиты
git add .
git commit -m "feat: implement Excel validation"

# Push
git push origin feature/excel-validation

# Создание Pull Request
```

---

## 🔄 СИНХРОНИЗАЦИЯ: ПАМЯТКА ДЛЯ РАЗРАБОТЧИКА

- Подробный поток: `project_progress/SYNC_FLOW.md` (форматы событий, порядок, лимиты, версияция).
- Быстрый запуск интеграционного теста синхронизации (PostgreSQL):

```bash
python testing/scripts/test_sync_integration.py --sync-type full --log-level INFO
python testing/scripts/test_sync_integration.py --sync-type incremental --period-months 6 --log-level DEBUG
```

- Интерпретация ключевых логов:
  - `Processed X main events + Y deferred events (queue size: N)` — если `N>0`, есть отложенные.
  - Отложенные `DealItemAdded` при «родитель не найден» — штатно для out‑of‑order; см. раздел Deferred.

- Проверка БД после прогона (примеры SQL):

```sql
SELECT COUNT(*) FROM read_deals;
SELECT COUNT(*) FROM read_positions WHERE is_active = true;
SELECT event_type, COUNT(*) FROM event_store GROUP BY event_type;
```

---

## 🏗️ АРХИТЕКТУРНЫЕ ПРИНЦИПЫ

### Domain Driven Design (DDD)

#### Domain Models

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List

@dataclass
class Deal:
    """Доменная модель сделки."""
    
    deal_id: str
    client_name: str
    invoice_number: str
    invoice_date: date
    revenue: Decimal
    margin: Decimal
    seller: str
    items: List['DealItem']
    
    def calculate_total_revenue(self) -> Decimal:
        """Вычисляет общую выручку по позициям."""
        return sum(item.total_price for item in self.items)
    
    def validate(self) -> None:
        """Валидирует данные сделки."""
        if self.revenue <= 0:
            raise ValueError("Revenue must be positive")
```

#### Value Objects

Система использует несколько типов value objects для денежных сумм с разной точностью:

```python
from decimal import Decimal
from domain.value_objects import Money, Money5, SignedMoney, SignedMoney5

# Money - для большинства денежных полей (2 знака после запятой)
revenue = Money(amount=Decimal("1500.50"))  # Округляется до 2 знаков

# Money5 - для purchase_price в DealItem (5 знаков после запятой)
purchase_price = Money5(amount=Decimal("123.45678"))  # Округляется до 5 знаков

# SignedMoney - для полей, которые могут быть отрицательными (2 знака)
margin = SignedMoney(amount=Decimal("-50.25"))  # Округляется до 2 знаков

# SignedMoney5 - для margin в DealItem (5 знаков после запятой)
margin_precise = SignedMoney5(amount=Decimal("-123.45678"))  # Округляется до 5 знаков
```

**Использование в DealItem:**
- `purchase_price`: `Money5` (5 знаков) - для точного хранения цены закупки
- `margin`: `SignedMoney5` (5 знаков) - для точного хранения маржи
- `sale_price`, `revenue`, `cost`: `Money` (2 знака) - стандартная точность

### Event Sourcing

#### Domain Events

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass
class DomainEvent:
    """Базовый класс для доменных событий."""
    
    event_type: str
    aggregate_id: str
    event_data: Dict[str, Any]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class DealCreated(DomainEvent):
    """Событие создания сделки."""
    
    def __init__(self, deal_id: str, deal_data: Dict[str, Any]):
        super().__init__(
            event_type="DealCreated",
            aggregate_id=deal_id,
            event_data=deal_data
        )
```

#### Event Store

```python
from typing import List, Optional
from src.domain.events import DomainEvent

class EventStore:
    """Хранилище событий."""
    
    async def append(self, events: List[DomainEvent]) -> None:
        """Добавляет события в хранилище."""
        for event in events:
            await self._save_event(event)
    
    async def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        """Получает события для агрегата."""
        # Реализация получения событий
        pass
```

### CQRS (Command Query Responsibility Segregation)

#### Commands

```python
from dataclasses import dataclass
from typing import List

@dataclass
class CreateDealCommand:
    """Команда создания сделки."""
    
    deal_id: str
    client_name: str
    invoice_number: str
    items: List[dict]

@dataclass
class UpdateDealCommand:
    """Команда обновления сделки."""
    
    deal_id: str
    changes: dict
```

#### Queries

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import date

@dataclass
class GetDealsQuery:
    """Запрос получения сделок."""
    
    page: int = 1
    size: int = 10
    client_name: Optional[str] = None
    seller: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

@dataclass
class GetDealByIdQuery:
    """Запрос получения сделки по ID."""
    
    deal_id: str
```

---

## 🔄 CI/CD

### GitHub Actions

#### .github/workflows/ci.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e ".[dev]"
    
    - name: Run tests
      env:
        DB_HOST: localhost
        DB_PORT: 5432
        DB_NAME: test_db
        DB_USER: postgres
        DB_PASSWORD: postgres
      run: |
        python -m pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Docker

#### Dockerfile

```dockerfile
# Backend
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .

# Точка входа: скрипт синхронизации или планировщик
CMD ["python", "-m", "src.application.sync_orchestrator"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=service_oper_uchet
      - DB_USER=postgres
      - DB_PASSWORD=password
    depends_on:
      - postgres
    volumes:
      - ./data:/app/data

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=service_oper_uchet
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 📊 МОНИТОРИНГ И ЛОГИРОВАНИЕ

### Логирование

#### Настройка логгера

```python
import logging
from loguru import logger

# Настройка логгера
logger.add(
    "logs/app.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)

# Использование в коде
logger.info("Starting sync session", session_id=session_id)
logger.error("Failed to parse Excel file", error=str(e))
```

#### Структурированное логирование

```python
import logging
from typing import Dict, Any

class StructuredLogger:
    """Структурированный логгер."""
    
    def log_sync_start(self, session_id: str, file_name: str) -> None:
        logger.info("Sync session started", extra={
            "session_id": session_id,
            "file_name": file_name,
            "event_type": "sync_start"
        })
    
    def log_sync_complete(self, session_id: str, stats: Dict[str, Any]) -> None:
        logger.info("Sync session completed", extra={
            "session_id": session_id,
            "stats": stats,
            "event_type": "sync_complete"
        })
```

### Метрики

Логирование метрик синхронизации через loguru (см. раздел Логирование выше). При необходимости можно добавить экспорт в Prometheus или другую систему мониторинга.

```python
# Пример: логирование метрик синхронизации
async def sync_excel_file(file_path: str) -> SyncResult:
    result = await process_file(file_path)
    logger.info("Sync completed", path=file_path, deals_count=len(result.deals))
    return result
```

---

## 🚀 РАЗВЕРТЫВАНИЕ

### Production развертывание

#### Системные требования

- **CPU**: 2+ ядра
- **RAM**: 4+ GB
- **Disk**: 20+ GB
- **OS**: Ubuntu 20.04+, CentOS 8+, Windows Server 2019+

#### Установка

```bash
# Клонирование
git clone https://github.com/Vitalylqw/service_oper_uchet.git
cd service_oper_uchet

# Установка зависимостей
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка БД
python scripts/database/create_schema.py
python scripts/database/init_database.py

# Запуск (скрипт синхронизации или планировщик)
python -m your_entry_script
```

#### Systemd сервис

```ini
# /etc/systemd/system/service-oper-uchet.service
[Unit]
Description=Service Oper Uchet (sync)
After=network.target postgresql.service

[Service]
Type=exec
User=service-oper-uchet
Group=service-oper-uchet
WorkingDirectory=/opt/service-oper-uchet
Environment=PATH=/opt/service-oper-uchet/venv/bin
ExecStart=/opt/service-oper-uchet/venv/bin/python -m your_entry_script
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx конфигурация

```nginx
# /etc/nginx/sites-available/service-oper-uchet
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/service-oper-uchet/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 🔧 ОТЛАДКА И ДИАГНОСТИКА

### Профилирование

#### cProfile для Python

```python
import cProfile
import pstats

def profile_function(func):
    """Декоратор для профилирования функций."""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)
        
        return result
    return wrapper

@profile_function
async def slow_function():
    # Код для профилирования
    pass
```

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

### Полезные команды

```bash
# Запуск в режиме разработки
# Проверка кода
ruff check . && black . --check && mypy src/

# Запуск всех тестов
python -m pytest

# Создание миграции
alembic revision --autogenerate -m "Add new field"

# Применение миграций
alembic upgrade head
```

### Полезные ссылки

- **[Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)** - паттерн Event Sourcing
- **[CQRS](https://martinfowler.com/bliki/CQRS.html)** - паттерн CQRS
- **[DDD](https://martinfowler.com/bliki/DomainDrivenDesign.html)** - Domain Driven Design

---

**Версия руководства**: 1.0  
**Дата обновления**: 27 января 2025  
**Для получения помощи**: создайте Issue в репозитории 