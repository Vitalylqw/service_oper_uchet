# 📋 API ДОКУМЕНТАЦИЯ SERVICE_OPER_UCHET

> **Версия API**: v1.0  
> **Базовый URL**: `http://localhost:8000`  
> **Формат**: JSON  
> **Аутентификация**: JWT Bearer Token

---

## 🔐 АУТЕНТИФИКАЦИЯ

### Получение токена доступа

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=viewer&password=password
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "viewer",
    "role": "viewer",
    "permissions": ["read:deals", "read:sessions"]
  }
}
```

### Использование токена

```http
GET /deals
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 👥 РОЛИ ПОЛЬЗОВАТЕЛЕЙ

| Роль | Описание | Разрешения |
|------|----------|------------|
| **viewer** | Просмотрщик | `read:deals`, `read:sessions` |
| **analyst** | Аналитик | `read:deals`, `read:sessions`, `write:sync` |
| **admin** | Администратор | Все разрешения |

---

## 🏥 HEALTH CHECK

### Проверка состояния системы

```http
GET /health
```

**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-27T10:30:00Z",
  "version": "0.2.0",
  "database": "connected",
  "services": {
    "event_store": "operational",
    "read_model_builder": "operational",
    "file_system": "operational"
  }
}
```

---

## 📊 СДЕЛКИ (DEALS)

### Получение списка сделок

```http
GET /deals?page=1&size=10&client_name=ООО&seller=Иванов
Authorization: Bearer <token>
```

**Параметры запроса:**
- `page` (int, optional): Номер страницы (по умолчанию: 1)
- `size` (int, optional): Размер страницы (по умолчанию: 10, максимум: 100)
- `client_name` (string, optional): Фильтр по названию клиента
- `seller` (string, optional): Фильтр по продавцу
- `invoice_date_from` (date, optional): Дата счета с
- `invoice_date_to` (date, optional): Дата счета по

**Ответ:**
```json
{
  "items": [
    {
      "id": 1,
      "deal_id": "DEAL-2025-001",
      "client_name": "ООО Рога и Копыта",
      "invoice_number": "INV-2025-001",
      "invoice_date": "2025-01-15",
      "revenue": 150000.00,
      "margin": 45000.00,
      "seller": "Иванов И.И.",
      "created_at": "2025-01-27T10:30:00Z",
      "updated_at": "2025-01-27T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 150,
    "pages": 15
  }
}
```

### Получение деталей сделки

```http
GET /deals/{deal_id}
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "id": 1,
  "deal_id": "DEAL-2025-001",
  "client_name": "ООО Рога и Копыта",
  "invoice_number": "INV-2025-001",
  "invoice_date": "2025-01-15",
  "revenue": 150000.00,
  "margin": 45000.00,
  "seller": "Иванов И.И.",
  "items": [
    {
      "id": 1,
      "product_name": "Товар 1",
      "quantity": 10,
      "unit_price": 15000.00,
      "total_price": 150000.00
    }
  ],
  "created_at": "2025-01-27T10:30:00Z",
  "updated_at": "2025-01-27T10:30:00Z"
}
```

### Статистика по сделкам

```http
GET /deals/stats
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "total_deals": 150,
  "total_revenue": 22500000.00,
  "total_margin": 6750000.00,
  "avg_revenue_per_deal": 150000.00,
  "avg_margin_percentage": 30.0,
  "top_sellers": [
    {
      "seller": "Иванов И.И.",
      "deals_count": 25,
      "total_revenue": 3750000.00
    }
  ],
  "top_clients": [
    {
      "client_name": "ООО Рога и Копыта",
      "deals_count": 15,
      "total_revenue": 2250000.00
    }
  ]
}
```

---

## 🔄 СЕССИИ СИНХРОНИЗАЦИИ

### Получение списка сессий

```http
GET /sessions?page=1&size=10&status=completed
Authorization: Bearer <token>
```

**Параметры запроса:**
- `page` (int, optional): Номер страницы
- `size` (int, optional): Размер страницы
- `status` (string, optional): Фильтр по статусу (pending, running, completed, failed)
- `created_at_from` (datetime, optional): Дата создания с
- `created_at_to` (datetime, optional): Дата создания по

**Ответ:**
```json
{
  "items": [
    {
      "id": 1,
      "session_id": "SYNC-2025-001",
      "status": "completed",
      "file_path": "/uploads/excel_file.xlsx",
      "total_deals": 15,
      "total_items": 84,
      "created_at": "2025-01-27T10:00:00Z",
      "completed_at": "2025-01-27T10:05:00Z",
      "duration_seconds": 300,
      "errors": []
    }
  ],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 25,
    "pages": 3
  }
}
```

### Получение деталей сессии

```http
GET /sessions/{session_id}
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "id": 1,
  "session_id": "SYNC-2025-001",
  "status": "completed",
  "file_path": "/uploads/excel_file.xlsx",
  "total_deals": 15,
  "total_items": 84,
  "created_at": "2025-01-27T10:00:00Z",
  "completed_at": "2025-01-27T10:05:00Z",
  "duration_seconds": 300,
  "changes": {
    "inserted": 99,
    "updated": 0,
    "deleted": 0
  },
  "errors": [],
  "warnings": [
    "Поле 'invoice_date' содержит некорректный формат даты в строке 15"
  ]
}
```

---

## 📤 СИНХРОНИЗАЦИЯ

### Загрузка Excel файла

```http
POST /sync/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: [Excel файл]
```

**Ответ:**
```json
{
  "session_id": "SYNC-2025-002",
  "status": "pending",
  "file_name": "oper_uchet_2025.xlsx",
  "file_size": 2048576,
  "message": "Файл загружен и поставлен в очередь на обработку"
}
```

### Запуск синхронизации

```http
POST /sync/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "SYNC-2025-002",
  "sync_type": "full"
}
```

**Параметры:**
- `session_id` (string, required): ID сессии синхронизации
- `sync_type` (string, optional): Тип синхронизации (full, incremental)

**Ответ:**
```json
{
  "session_id": "SYNC-2025-002",
  "status": "running",
  "message": "Синхронизация запущена",
  "estimated_duration": 300
}
```

### Отмена синхронизации

```http
POST /sync/cancel
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "SYNC-2025-002"
}
```

**Ответ:**
```json
{
  "session_id": "SYNC-2025-002",
  "status": "cancelled",
  "message": "Синхронизация отменена"
}
```

---

## 📈 СТАТИСТИКА И МОНИТОРИНГ

### Общая статистика системы

```http
GET /stats/overview
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "system": {
    "uptime_seconds": 86400,
    "version": "0.2.0",
    "database_size_mb": 45.2
  },
  "data": {
    "total_deals": 150,
    "total_items": 1250,
    "total_sessions": 25,
    "last_sync": "2025-01-27T10:00:00Z"
  },
  "performance": {
    "avg_sync_duration_seconds": 180,
    "success_rate_percentage": 96.0,
    "avg_api_response_time_ms": 45
  }
}
```

### Статистика по периодам

```http
GET /stats/periods?period=month&from=2025-01-01&to=2025-01-31
Authorization: Bearer <token>
```

**Параметры:**
- `period` (string, required): Период группировки (day, week, month, year)
- `from` (date, required): Дата начала периода
- `to` (date, required): Дата окончания периода

**Ответ:**
```json
{
  "period": "month",
  "from": "2025-01-01",
  "to": "2025-01-31",
  "data": [
    {
      "period": "2025-01-01",
      "deals_count": 5,
      "revenue": 750000.00,
      "margin": 225000.00
    }
  ]
}
```

---

## ⚠️ ОБРАБОТКА ОШИБОК

### Стандартная структура ошибки

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Некорректные данные в запросе",
    "details": [
      {
        "field": "invoice_date",
        "message": "Неверный формат даты"
      }
    ]
  }
}
```

### Коды ошибок

| Код | HTTP Status | Описание |
|-----|-------------|----------|
| `AUTHENTICATION_ERROR` | 401 | Ошибка аутентификации |
| `AUTHORIZATION_ERROR` | 403 | Недостаточно прав |
| `VALIDATION_ERROR` | 422 | Ошибка валидации данных |
| `NOT_FOUND` | 404 | Ресурс не найден |
| `CONFLICT` | 409 | Конфликт данных |
| `INTERNAL_ERROR` | 500 | Внутренняя ошибка сервера |

### Примеры ошибок

#### Ошибка аутентификации
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=invalid&password=wrong
```

**Ответ:**
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Неверные учетные данные"
  }
}
```

#### Ошибка валидации
```http
POST /sync/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: [неверный файл]
```

**Ответ:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Некорректный файл",
    "details": [
      {
        "field": "file",
        "message": "Поддерживаются только Excel файлы (.xlsx, .xls)"
      }
    ]
  }
}
```

---

## 🔧 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Python (requests)

```python
import requests

# Аутентификация
auth_response = requests.post(
    "http://localhost:8000/auth/login",
    data={"username": "viewer", "password": "password"}
)
token = auth_response.json()["access_token"]

# Получение сделок
headers = {"Authorization": f"Bearer {token}"}
deals_response = requests.get(
    "http://localhost:8000/deals?page=1&size=10",
    headers=headers
)
deals = deals_response.json()
```

### JavaScript (fetch)

```javascript
// Аутентификация
const authResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: 'username=viewer&password=password'
});
const { access_token } = await authResponse.json();

// Получение сделок
const dealsResponse = await fetch('http://localhost:8000/deals?page=1&size=10', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
const deals = await dealsResponse.json();
```

### cURL

```bash
# Аутентификация
TOKEN=$(curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=viewer&password=password" \
  | jq -r '.access_token')

# Получение сделок
curl -X GET "http://localhost:8000/deals?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

**Версия документации**: 1.0  
**Дата обновления**: 27 января 2025 