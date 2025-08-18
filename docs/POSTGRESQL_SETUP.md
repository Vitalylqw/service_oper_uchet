# PostgreSQL Setup Guide

## Обзор
Проект настроен для работы с PostgreSQL контейнером `so_pg` в сети `devnet`.

## Конфигурация

### Файл config.env
```bash
# Database Configuration
DB_TYPE=postgresql
DB_HOST=so_pg          # Имя контейнера PostgreSQL
DB_PORT=5432           # Стандартный порт PostgreSQL
DB_NAME=so_uchet      # Имя базы данных
DB_USER=so_user       # Пользователь БД
DB_PASSWORD=so_pass   # Пароль пользователя
```

### Docker Compose (docker-compose.db.yml)
```yaml
services:
  postgres:
    image: postgres:16
    container_name: so_pg
    environment:
      POSTGRES_DB: so_uchet
      POSTGRES_USER: so_user
      POSTGRES_PASSWORD: so_pass
    networks:
      - devnet
```

## Подключение

### Автоматическое подключение
Проект автоматически подключается к PostgreSQL при запуске:
- Host: `so_pg` (имя контейнера)
- Port: `5432`
- Database: `so_uchet`
- User: `so_user`
- Password: `so_pass`

### Проверка подключения
```bash
python scripts/test_postgres_connection.py
```

## Скрипты управления

### Запуск PostgreSQL
```bash
scripts/start_postgres.bat
```

### Остановка PostgreSQL
```bash
scripts/stop_postgres.bat
```

### Проверка статуса
```bash
scripts/check_postgres_status.bat
```

## Сетевая конфигурация

### Dev Container
- Сеть: `172.18.0.0/16`
- IP: `172.18.0.3`
- Gateway: `172.18.0.1`

### PostgreSQL Container
- Сеть: `devnet` (внешняя)
- Имя: `so_pg`
- Порт: `5432`

## Troubleshooting

### Проблема: Connection refused
**Решение**: Убедитесь, что контейнер PostgreSQL запущен
```bash
scripts/check_postgres_status.bat
```

### Проблема: Host not found
**Решение**: Проверьте, что контейнер в сети `devnet`
```bash
docker network ls | grep devnet
```

### Проблема: Authentication failed
**Решение**: Проверьте учетные данные в `config.env`

## Тестирование

### Unit тесты
```bash
python -m pytest tests/unit/ --tb=line
```

### Integration тесты
```bash
python -m pytest tests/integration/ --tb=line
```

### E2E тесты
```bash
python -m pytest tests/e2e/ --tb=line
```

## Безопасность

### Production настройки
1. Измените пароли по умолчанию
2. Настройте SSL соединения
3. Используйте connection pooling
4. Ограничьте доступ по IP
