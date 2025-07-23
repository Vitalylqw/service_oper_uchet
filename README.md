# 🏢 Enterprise Data Synchronization System

**Система синхронизации корпоративных данных** для автоматизации процессов управления продажами с интеграцией Excel и 1С Предприятие.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Описание

Комплексная система для автоматической синхронизации данных о продажах между Excel файлами и корпоративной базой данных с полной интеграцией 1С Предприятие, продвинутой валидацией и enterprise-уровнем мониторинга.

### 🚀 Ключевые возможности

- 🔄 **Умная синхронизация**: полная и инкрементальная синхронизация с настраиваемыми периодами
- 🛡️ **Продвинутая валидация**: контроль структуры Excel, финансовая сверка, обнаружение сдвигов данных
- 🔗 **Интеграция с 1С**: автоматическая сверка данных через API, выявление расхождений
- 📊 **Веб-интерфейс**: современный UI для просмотра, поиска и управления данными
- 📈 **Мониторинг**: dashboard с аналитикой, системой предупреждений и отчетами
- 🧪 **Высокое покрытие тестами**: 85%+ общее покрытие, 95%+ для критичных компонентов
- 🔐 **Enterprise-безопасность**: ролевая модель, аудит всех операций
- ⚡ **Высокая производительность**: поддержка файлов до 50MB, обработка 1000+ сделок

## 📋 Документация

- **[Техническое задание](technical_requirements.txt)** - полная спецификация системы
- **[Статус проекта](HANDOVER_STATUS.md)** - текущее состояние разработки и план задач
- **[Архитектурный план](PROJECT_PLAN.md)** - концептуальный план реализации
- **[Итоговый план](PROJECT_PLAN_FINAL.md)** - финальная архитектура системы
- **[Исходные данные](Data_source_excel.xlsx)** - 🔒 **ВАЖНО**: тестовый Excel файл с примерами данных
- **[Database Design](docs/database_design.md)** - архитектура базы данных *(скоро)*
- **[API Documentation](docs/api.md)** - REST API спецификация *(скоро)*
- **[User Guide](docs/user_guide.md)** - руководство пользователя *(скоро)*

### 🔒 Защищенные файлы
>
> **Внимание**: Следующие файлы критичны для проекта и защищены от случайного удаления:
>
> - `Data_source_excel.xlsx` - исходные данные для тестирования и валидации
> - `HANDOVER_STATUS.md` - отслеживание прогресса разработки
> - `PROJECT_PLAN.md` - архитектурная документация

## 🏗️ Архитектура

Система построена по принципам **Domain Driven Design (DDD)** с разделением на архитектурные слои:

``` text
src/
├── domain/              # Бизнес-логика предметной области
│   ├── entities/        # Сущности (Deal, DealItem)
│   ├── value_objects/   # Объекты-значения
│   └── services/        # Доменные сервисы
├── application/         # Сценарии использования
│   ├── use_cases/       # Бизнес-сценарии
│   ├── services/        # Сервисы приложения
│   └── dto/            # Объекты передачи данных
├── infrastructure/      # Внешние сервисы
│   ├── database/        # БД и репозитории
│   ├── excel/          # Excel парсинг и валидация
│   ├── onec/           # Интеграция с 1С
│   └── scheduling/     # Планировщик задач
└── presentation/        # Пользовательские интерфейсы
    ├── api/            # REST API
    └── web/            # Web UI
```

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.9+
- PostgreSQL 16+
- 1С Предприятие с настроенным API
- Git

### 1. Клонирование и установка

```bash
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
```

### 2. Настройка конфигурации

Создайте файл `.env` с настройками:

```env
# Database Configuration
DB_HOST=192.168.31.2
DB_PORT=5432
DB_NAME=corp
DB_USER=etl
DB_PASSWORD=your_password

# 1C Integration
ONEC_API_URL=http://your-1c-server:8080/api/v1
ONEC_USERNAME=api_user
ONEC_PASSWORD=api_password

# Application Settings
APP_HOST=192.168.1.51
APP_PORT=8000
DEBUG=False

# Sync Settings
SYNC_SCHEDULE=03:00
FULL_SYNC_FREQUENCY=weekly
INCREMENTAL_MONTHS=3

# File Monitoring
FILE_SOURCE_PATH=\\remote-computer\shared\data
FILE_MONITOR_INTERVAL=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/sync.log
```

### 3. Инициализация базы данных

```bash
# Создание схемы БД
alembic upgrade head

# Создание начальных данных
python scripts/init_data.py
```

### 4. Запуск системы

```bash
# Запуск веб-приложения
uvicorn main:app --host 0.0.0.0 --port 8000

# Запуск планировщика (отдельный процесс)
python scripts/scheduler.py

# Ручная синхронизация (для тестирования)
python scripts/manual_sync.py
```

### 5. Доступ к системе

- **Web UI**: <http://192.168.1.51:8000>
- **API Docs**: <http://192.168.1.51:8000/docs>
- **Мониторинг**: <http://192.168.1.51:8000/monitoring>

## 🔧 Возможности системы

### 📊 Типы синхронизации

- **Полная синхронизация**: обработка всех данных (по умолчанию еженедельно)
- **Инкрементальная**: только последние N месяцев (по умолчанию 3)
- **Автоматическое переключение**: система выбирает оптимальный режим

### 🛡️ Система валидации

- **Контроль структуры**: проверка заголовков и позиций в Excel
- **Финансовая сверка**: сумма строк = итоговые показатели
- **Обнаружение сдвигов**: выявление смещений данных
- **Сверка с 1С**: автоматическая проверка через API

### 🔍 Веб-интерфейс

- **Dashboard**: статистика синхронизации, графики изменений
- **Каталог сделок**: поиск, фильтрация, сортировка
- **Детальный просмотр**: полная информация о сделке с историей
- **Мониторинг**: журнал синхронизации, предупреждения
- **Админ-панель**: настройки системы, управление пользователями

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Только unit тесты
pytest tests/unit/

# Только интеграционные тесты
pytest tests/integration/

# E2E тесты
pytest tests/e2e/

# Нагрузочные тесты
pytest tests/performance/
```

### Требования к покрытию

- **Общее покрытие**: минимум 85%
- **Критичные компоненты**: минимум 95%
- **Автоматическая проверка**: в CI/CD пайплайне

## 🛠️ Разработка

### Стандарты кода

```bash
# Линтинг
ruff check .

# Форматирование
black .

# Проверка типов
mypy src/

# Исправление проблем
ruff check --fix .
```

### Коммиты

Используется [Conventional Commits](https://www.conventionalcommits.org/):

``` text
feat: add 1C integration for data verification
fix: resolve Excel parsing error with shifted data
docs: update technical requirements
test: add unit tests for validation module
```

## 📈 Мониторинг и метрики

### Ключевые метрики

- **Успешность синхронизации**: процент успешных операций
- **Время выполнения**: полная (<15 мин) и инкрементальная (<3 мин)
- **Качество данных**: процент валидных записей
- **Расхождения с 1С**: количество несоответствий

### Алерты

- Email уведомления о критических ошибках
- Предупреждения о проблемах с данными
- Отчеты о результатах синхронизации
- Мониторинг производительности

## 🔐 Безопасность

- **Аутентификация**: токен-based доступ
- **Авторизация**: ролевая модель доступа
- **Аудит**: логирование всех операций
- **Шифрование**: HTTPS/TLS для всех соединений

## 📊 Производительность

- **Обработка данных**: до 1000 сделок за 5 минут
- **Размер файлов**: поддержка до 50 MB
- **API отклик**: менее 2 секунд
- **Одновременные пользователи**: до 50

## 🚀 Деплой

### Системные требования

- **ОС**: Windows 10+, Linux, macOS
- **RAM**: минимум 4 GB, рекомендуется 8 GB
- **Диск**: 10 GB свободного места
- **Сеть**: доступ к PostgreSQL и 1С

### Развертывание

```bash
# Продакшн запуск
gunicorn main:app --bind 0.0.0.0:8000 --workers 4

# Systemd сервис (Linux)
sudo systemctl enable service-oper-uchet
sudo systemctl start service-oper-uchet

# Windows Service
python scripts/install_service.py
```

## 📞 Поддержка

### Получение помощи

1. Проверьте [Issues](https://github.com/Vitalylqw/service_oper_uchet/issues)
2. Просмотрите [Техническое задание](technical_requirements.txt)
3. Создайте новый Issue с описанием проблемы

### Структура Issue

``` text
**Тип проблемы**: Bug/Feature Request/Question
**Окружение**: Windows 10, Python 3.9, PostgreSQL 16
**Описание**: Детальное описание проблемы
**Шаги воспроизведения**: 1. ... 2. ... 3. ...
**Ожидаемый результат**: Что должно произойти
**Фактический результат**: Что произошло
**Логи**: Приложите relevant логи (без конфиденциальных данных)
```

## 🤝 Участие в разработке

1. Fork репозитория
2. Создайте feature branch: `git checkout -b feature/amazing-feature`
3. Commit изменения: `git commit -m 'feat: add amazing feature'`
4. Push в branch: `git push origin feature/amazing-feature`
5. Создайте Pull Request

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🏆 Статус проекта

- **Версия**: 0.2.0
- **Статус**: Active Development
- **Последнее обновление**: 2025-01-XX
- **Техническое задание**: [Версия 2.1](technical_requirements.txt)

---

**Разработано для**: Корпоративные системы управления продажами  
**Платформа**: Cross-platform (Windows, Linux, macOS)  
**Интеграция**: PostgreSQL, 1С Предприятие, Excel  
**Архитектура**: DDD, Event Sourcing, CQRS
