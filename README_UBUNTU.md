# Service Oper Uchet - Ubuntu Setup

## Требования
- Ubuntu 20.04+
- Docker и Docker Compose
- Cursor IDE с dev-container расширением

## Быстрый старт

### 1. Клонирование и запуск
```bash
git clone <repository-url>
cd service_oper_uchet
```

### 2. Запуск базы данных
```bash
# Создать сеть и запустить PostgreSQL
./scripts/services/start_from_host.sh
```

### 3. Запуск через dev-container
1. Откройте проект в Cursor
2. Выберите "Reopen in Container" когда появится предложение
3. Дождитесь создания контейнера

### 4. Запуск backend
```bash
# В dev-container терминале
./scripts/services/start_backend.sh
```

## Ручной запуск компонентов

### База данных
```bash
./scripts/services/start_from_host.sh
```

### Backend API
```bash
./scripts/services/start_backend.sh
```

## Доступные сервисы
- **API**: http://localhost:8000
- **Database**: localhost:5432

## Остановка сервисов
```bash
# Остановить backend
pkill -f "uvicorn.*main:app"

# Остановить БД
docker-compose -f docker-compose.db.yml down
```

## Устранение проблем

### Порт занят
```bash
sudo lsof -i :8000  # Проверить что использует порт
sudo kill -9 <PID>  # Остановить процесс
```

### Проблемы с Docker
```bash
docker system prune  # Очистить неиспользуемые ресурсы
docker-compose -f docker-compose.db.yml down  # Остановить БД
```

### Проблемы с зависимостями
```bash
# Python
pip install -r requirements.txt
```

## Архитектура
- **Dev-container**: только Python/FastAPI backend
- **База данных**: отдельный PostgreSQL контейнер
- **Web-часть**: пока не реализована (бэкенд в разработке)
