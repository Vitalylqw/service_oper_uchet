# Гибридный подход с отложенными событиями

## 📋 Обзор

Реализован гибридный подход для обработки событий в системе Event Sourcing + CQRS:

1. **Основная логика**: Правильный порядок создания событий в оркестраторе
2. **Защитный механизм**: Очередь отложенных событий для обработки неудачных событий
3. **Информативность**: Детальное логирование причин отложений

## 🏗️ Архитектура

### Компоненты

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Orchestrator  │    │   Event Store   │    │ ReadModelBuilder│
│                 │    │                 │    │                 │
│ ✅ DealCreated  │───▶│ aggregate_id    │───▶│ ✅ Process      │
│ ✅ DealItemAdded│    │ sequence_number │    │ ❌ Defer        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                              ┌─────────────────┐
                                              │ Deferred Queue  │
                                              │                 │
                                              │ 🔄 Retry Logic  │
                                              │ 📊 Metrics      │
                                              └─────────────────┘
```

### Поток данных

1. **Создание событий**: Оркестратор создает события в правильном порядке
2. **Хранение**: Event Store сохраняет с правильной сортировкой
3. **Обработка**: ReadModelBuilder обрабатывает события по порядку
4. **Отложенная обработка**: Неудачные события попадают в очередь
5. **Повторные попытки**: Автоматические retry с экспоненциальной задержкой

## 🔧 Реализация

### 1. DeferredEventQueue

```python
class DeferredEventQueue:
    def __init__(self, max_retries: int = 3):
        self.queue: List[DeferredEvent] = []
        self.max_retries = max_retries
        self.metrics = DeferredEventMetrics()
```

**Функции:**
- Добавление событий с причинами отложений
- Автоматические повторные попытки
- Экспоненциальная задержка (5, 15, 60 минут)
- Сбор метрик и статистики

### 2. Правильная сортировка событий

```python
# В EventStore.get_latest_events()
query = (
    select(EventStoreModel)
    .order_by(EventStoreModel.aggregate_id, EventStoreModel.sequence_number)
    .limit(limit)
)
```

**Преимущества:**
- События одной сделки обрабатываются вместе
- Правильный порядок внутри сделки
- Соответствие принципам Event Sourcing

### 3. Гибридная обработка в ReadModelBuilder

```python
async def process_latest_events(self, limit: int = 100, auto_commit: bool = True) -> int:
    # 1. Обрабатываем основные события
    main_processed = await self._process_main_events(limit)
    
    # 2. Обрабатываем отложенные события
    deferred_processed = await self.deferred_queue.process_deferred_events(
        self._process_single_event
    )
    
    return main_processed + deferred_processed
```

### 4. Отложенная обработка DealItemAdded

```python
# В _create_deal_item_read_model()
deal_context = await self._get_deal_context(item.deal_id)

if not deal_context:
    # Отложенная обработка - родительская сделка не найдена
    reason = f"Parent deal {item.deal_id} not found in read model"
    await self.deferred_queue.add_event(full_event, reason)
    return
```

## 📊 Метрики и мониторинг

### DeferredEventMetrics

```python
{
    "total_deferred": 5,
    "successful_retries": 3,
    "failed_retries": 1,
    "permanent_failures": 1,
    "reasons": {
        "Parent deal not found": 3,
        "Invalid period data": 2
    },
    "event_types": {
        "DealItemAdded": 4,
        "DealCreated": 1
    }
}
```

### Логирование

```
WARNING | Event deferred: DealItemAdded for deal-123 - Parent deal not found
INFO   | Retrying deferred event: DealItemAdded (attempt 1/3)
SUCCESS| Successfully processed deferred event: DealItemAdded
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Windows
scripts/test/test_hybrid_deferred_events.bat

# Linux/Mac
python scripts/test/test_hybrid_deferred_events.py
```

### Тестовые сценарии

1. **Правильный порядок событий**
2. **Отложенная обработка при отсутствии родительской сделки**
3. **Автоматические повторные попытки**
4. **Метрики и статистика**
5. **Обработка постоянных ошибок**

## ✅ Преимущества гибридного подхода

### Надежность
- Система продолжает работать даже при проблемах
- Автоматическое восстановление после временных ошибок
- Защита от потери данных

### Производительность
- Основная логика остается быстрой
- Отложенная обработка не блокирует основной поток
- Эффективное использование ресурсов

### Информативность
- Четкие причины отложений
- Детальная статистика
- Возможность мониторинга проблем

### Гибкость
- Настраиваемые политики повторных попыток
- Возможность расширения для других типов ошибок
- Адаптация к различным сценариям

## 🔄 Жизненный цикл отложенного события

```
1. Событие создается в оркестраторе
   ↓
2. Сохраняется в Event Store
   ↓
3. ReadModelBuilder пытается обработать
   ↓
4. ❌ Ошибка → Событие попадает в очередь
   ↓
5. ⏰ Через 5 минут → Первая повторная попытка
   ↓
6. ❌ Ошибка → Через 15 минут → Вторая попытка
   ↓
7. ❌ Ошибка → Через 60 минут → Третья попытка
   ↓
8. ❌ Ошибка → Постоянная ошибка → Логирование
```

## 🎯 Рекомендации по использованию

### Настройка

1. **Количество повторных попыток**: 3 (по умолчанию)
2. **Задержки**: 5, 15, 60 минут
3. **Логирование**: Уровень WARNING для отложений

### Мониторинг

1. **Регулярная проверка метрик**
2. **Анализ причин отложений**
3. **Настройка алертов для постоянных ошибок**

### Оптимизация

1. **Анализ паттернов отложений**
2. **Настройка задержек под нагрузку**
3. **Масштабирование при необходимости**

## 🚀 Будущие улучшения

1. **Персистентная очередь** (Redis/RabbitMQ)
2. **Распределенная обработка**
3. **Веб-интерфейс для мониторинга**
4. **Интеграция с системами алертов**
5. **Машинное обучение для оптимизации retry стратегий**