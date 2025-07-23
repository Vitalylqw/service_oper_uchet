# 🚀 FastAPI Documentation

## 🛠️ Настройка

### 1. Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

**Обязательно измените SECRET_KEY для production!**

### 2. Запуск API

```bash
# Development
uvicorn src.presentation.api.main:app --reload --host 0.0.0.0 --port 8000

# Production  
uvicorn src.presentation.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Доступные URL

- **📖 API Docs**: <http://localhost:8000/docs>
- **🔧 ReDoc**: <http://localhost:8000/redoc>
- **❤️ Health Check**: <http://localhost:8000/health/>
- **📊 Root Info**: <http://localhost:8000/>

## 🔐 Аутентификация

### Тестовые пользователи

| Username | Password | Role | Доступ |
|----------|----------|------|--------|
| admin | admin123 | admin | Полный доступ |
| analyst | analyst123 | analyst | Чтение + создание сессий |  
| viewer | viewer123 | viewer | Только чтение |

### Логин

```bash
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
```

**Ответ:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", 
  "token_type": "bearer",
  "expires_in": 900
}
```

### Использование токена

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/v1/deals/"
```

## 📊 API Endpoints

### 🔐 Authentication (`/auth`)

- `POST /auth/login` - Логин
- `GET /auth/me` - Информация о текущем пользователе
- `GET /auth/users` - Список пользователей (admin only)
- `POST /auth/users` - Создать пользователя (admin only)

### 💼 Deals (`/api/v1/deals`)

- `GET /api/v1/deals/` - Список сделок с пагинацией и фильтрами
- `GET /api/v1/deals/{id}` - Детали сделки  
- `GET /api/v1/deals/{id}/history` - История изменений сделки
- `GET /api/v1/deals/stats/summary` - Статистика по сделкам

### ⚙️ Sync Sessions (`/api/v1/sessions`)

- `GET /api/v1/sessions/` - Список сессий синхронизации
- `GET /api/v1/sessions/{id}` - Детали сессии
- `POST /api/v1/sessions/` - Создать сессию (analyst+)
- `DELETE /api/v1/sessions/{id}` - Отменить сессию (analyst+)
- `GET /api/v1/sessions/{id}/logs` - Логи сессии
- `GET /api/v1/sessions/stats/summary` - Статистика синхронизации

### ❤️ Health (`/health`)

- `GET /health/` - Общий статус системы
- `GET /health/ready` - Готовность (для Kubernetes)
- `GET /health/live` - Жизнь (для Kubernetes)  
- `GET /health/metrics` - Метрики системы

## 🔍 Примеры запросов

### Список сделок с фильтрами

```bash
curl -H "Authorization: Bearer TOKEN" \
"http://localhost:8000/api/v1/deals/?page=1&limit=10&client_name=Компания&is_shipped=true"
```

### Создание сессии синхронизации  

```bash
curl -X POST \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"session_type": "incremental", "file_path": "/data/file.xlsx"}' \
     "http://localhost:8000/api/v1/sessions/"
```

### Статистика сделок по периоду

```bash
curl -H "Authorization: Bearer TOKEN" \
"http://localhost:8000/api/v1/deals/stats/summary?period_year=2024&period_month=01"
```

## 🎯 Статусы ответов

- **200** - OK
- **201** - Created  
- **400** - Bad Request
- **401** - Unauthorized (неверный токен)
- **403** - Forbidden (недостаточно прав)
- **404** - Not Found
- **422** - Validation Error
- **500** - Internal Server Error

## 📋 Пагинация

Все list endpoints поддерживают пагинацию:

**Параметры:**

- `page` (int): номер страницы (начиная с 1)
- `limit` (int): элементов на странице (1-100)

**Ответ:**

```json
{
  "items": [...],
  "total": 150,
  "page": 1, 
  "limit": 20,
  "pages": 8
}
```

## 🛡️ RBAC (Role-Based Access Control)

### Роли

1. **👁️ viewer** - Только чтение данных
2. **📊 analyst** - Чтение + создание/отмена сессий синхронизации
3. **🔧 admin** - Полный доступ + управление пользователями

### Матрица доступа

| Endpoint | viewer | analyst | admin |
|----------|--------|---------|-------|
| GET deals | ✅ | ✅ | ✅ |
| GET sessions | ✅ | ✅ | ✅ |
| POST sessions | ❌ | ✅ | ✅ |
| DELETE sessions | ❌ | ✅ | ✅ |
| User management | ❌ | ❌ | ✅ |

## 🧪 Статус

**Текущий статус:** MVP с mock данными

**Готово:**

- ✅ JWT аутентификация + RBAC
- ✅ Все endpoints с валидацией
- ✅ Пагинация и фильтрация
- ✅ OpenAPI документация
- ✅ Health checks
- ✅ 67 unit тестов (100% покрытие)

**TODO для production:**

- 🔄 Интеграция с реальными сервисами Sprint 1
- 🔄 Настоящая БД пользователей
- 🔄 Refresh token логика
- 🔄 Real-time логи
- 🔄 Метрики производительности
