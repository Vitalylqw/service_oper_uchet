# 👨‍💻 РУКОВОДСТВО РАЗРАБОТЧИКА SERVICE_OPER_UCHET

> **Версия**: 1.0  
> **Дата обновления**: 27 января 2025  
> **Для**: Разработчики, DevOps, архитекторы

---

## 🎯 ОБЗОР АРХИТЕКТУРЫ

### Технический стек

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Backend** | FastAPI | 0.104+ | REST API сервер |
| **Database** | PostgreSQL/SQLite | 16+/3.35+ | Хранение данных |
| **Frontend** | React + TypeScript | 18+ | Веб-интерфейс |
| **Build Tool** | Vite | 5.0+ | Сборка фронтенда |
| **Testing** | pytest + Vitest | 7.4+ | Тестирование |
| **Linting** | Ruff + ESLint | 0.1+ | Анализ кода |
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
└── presentation/        # Пользовательские интерфейсы
    ├── api/            # REST API (FastAPI)
    └── web/            # Web UI (React)
```

---

## 🚀 НАСТРОЙКА ОКРУЖЕНИЯ РАЗРАБОТКИ

### Предварительные требования

```bash
# Python 3.9+
python --version

# Node.js 18+
node --version

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

#### Frontend (React)

```bash
# Переход в папку фронтенда
cd src/presentation/web

# Установка зависимостей
npm install

# Проверка установки
npm run build
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

#### Frontend тесты

```bash
# Переход в папку фронтенда
cd src/presentation/web

# Запуск тестов
npm test

# Запуск тестов в watch режиме
npm run test:watch

# Запуск тестов с покрытием
npm run test:coverage
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
from src.infrastructure.database.connection import get_database_session

class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_deal_repository_crud(self, test_database):
        # Arrange
        async with get_database_session() as session:
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

#### Frontend тесты (React)

```typescript
import { render, screen } from '@testing-library/react';
import { DealsTable } from '../DealsTable';

describe('DealsTable', () => {
  it('renders deals correctly', () => {
    const mockDeals = [
      {
        id: 1,
        deal_id: 'DEAL-001',
        client_name: 'Test Client',
        revenue: 100000
      }
    ];

    render(<DealsTable deals={mockDeals} />);
    
    expect(screen.getByText('Test Client')).toBeInTheDocument();
    expect(screen.getByText('DEAL-001')).toBeInTheDocument();
  });
});
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

#### TypeScript (ESLint + Prettier)

```typescript
// ✅ Правильно
interface Deal {
  id: number;
  dealId: string;
  clientName: string;
  revenue: number;
  margin: number;
}

const DealCard: React.FC<{ deal: Deal }> = ({ deal }) => {
  return (
    <div className="deal-card">
      <h3>{deal.clientName}</h3>
      <p>Revenue: ${deal.revenue.toLocaleString()}</p>
    </div>
  );
};
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

#### Frontend

```bash
# Переход в папку фронтенда
cd src/presentation/web

# Проверка кода
npm run lint

# Автоматическое исправление
npm run lint:fix

# Форматирование
npm run format
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

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    """Value object для денежных сумм."""
    
    amount: Decimal
    currency: str = "RUB"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
```

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

EXPOSE 8000

CMD ["uvicorn", "src.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
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

  frontend:
    build: ./src/presentation/web
    ports:
      - "3000:3000"
    depends_on:
      - api

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

#### Prometheus метрики

```python
from prometheus_client import Counter, Histogram, Gauge

# Метрики
sync_requests_total = Counter('sync_requests_total', 'Total sync requests')
sync_duration_seconds = Histogram('sync_duration_seconds', 'Sync duration')
active_sync_sessions = Gauge('active_sync_sessions', 'Active sync sessions')

# Использование в коде
@sync_requests_total.count_exceptions()
@sync_duration_seconds.time()
async def sync_excel_file(file_path: str) -> SyncResult:
    active_sync_sessions.inc()
    try:
        result = await process_file(file_path)
        return result
    finally:
        active_sync_sessions.dec()
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

# Запуск
gunicorn src.presentation.api.main:app --bind 0.0.0.0:8000 --workers 4
```

#### Systemd сервис

```ini
# /etc/systemd/system/service-oper-uchet.service
[Unit]
Description=Service Oper Uchet API
After=network.target postgresql.service

[Service]
Type=exec
User=service-oper-uchet
Group=service-oper-uchet
WorkingDirectory=/opt/service-oper-uchet
Environment=PATH=/opt/service-oper-uchet/venv/bin
ExecStart=/opt/service-oper-uchet/venv/bin/gunicorn src.presentation.api.main:app --bind 0.0.0.0:8000 --workers 4
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

### Отладка API

#### Логирование запросов

```python
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    
    return response
```

#### Health checks

```python
from fastapi import APIRouter
from src.infrastructure.database.connection import get_database_session

router = APIRouter()

@router.get("/health")
async def health_check():
    """Проверка состояния системы."""
    try:
        # Проверка БД
        async with get_database_session() as session:
            await session.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

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
python -m uvicorn src.presentation.api.main:app --reload

# Запуск фронтенда
cd src/presentation/web && npm run dev

# Проверка кода
ruff check . && black . --check && mypy src/

# Запуск всех тестов
python -m pytest && cd src/presentation/web && npm test

# Создание миграции
alembic revision --autogenerate -m "Add new field"

# Применение миграций
alembic upgrade head
```

### Полезные ссылки

- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - документация FastAPI
- **[React Documentation](https://react.dev/)** - документация React
- **[Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)** - паттерн Event Sourcing
- **[CQRS](https://martinfowler.com/bliki/CQRS.html)** - паттерн CQRS
- **[DDD](https://martinfowler.com/bliki/DomainDrivenDesign.html)** - Domain Driven Design

---

**Версия руководства**: 1.0  
**Дата обновления**: 27 января 2025  
**Для получения помощи**: создайте Issue в репозитории 