# Команды миграций

## Назначение

Этот документ содержит рабочие команды Alembic для текущего состояния репозитория. Он не описывает
исторические эксперименты со структурой миграций.

## Базовые команды

Проверить текущую версию:

```bash
alembic current
alembic current -v
```

Посмотреть историю:

```bash
alembic history
alembic history --verbose
```

Проверить расхождение моделей и схемы:

```bash
alembic check
```

## Применение миграций

Применить все миграции:

```bash
alembic upgrade head
```

Применить следующую миграцию:

```bash
alembic upgrade +1
```

Показать SQL без выполнения:

```bash
alembic upgrade head --sql
```

## Откат

Откат на одну миграцию:

```bash
alembic downgrade -1
```

Откат к конкретной ревизии:

```bash
alembic downgrade <revision>
```

Полный откат:

```bash
alembic downgrade base
```

Показать SQL отката:

```bash
alembic downgrade -1 --sql
```

## Создание новых миграций

Автогенерация:

```bash
alembic revision --autogenerate -m "Describe change"
```

Пустая миграция:

```bash
alembic revision -m "Describe change"
```

Просмотр конкретной ревизии:

```bash
alembic show <revision>
```

## Типовые сценарии

### Чистая dev-БД

```bash
docker-compose -f docker-compose.db.yml up -d
alembic upgrade head
python scripts/test/test_postgres_connection.py
```

### После изменения SQLAlchemy моделей

```bash
alembic check
alembic revision --autogenerate -m "Describe change"
alembic upgrade head
```

### Перед review миграции

```bash
alembic upgrade head --sql
```

## Важные замечания

- перед risky-изменениями делайте backup БД;
- не используйте `stamp` без явного понимания, почему версия в БД должна быть изменена вручную;
- описание миграции должно отражать причину изменения, а не только механическое действие;
- после миграции нужно проверить не только схему, но и рабочие сценарии sync flow.

## Что считать источником истины

Каноника по миграциям определяется комбинацией:

- `migrations/versions/*.py`
- `migrations/env.py`
- `src/infrastructure/database/models.py`

Если старый документ по миграциям противоречит этим файлам, ориентироваться нужно на код и текущие
ревизии Alembic.







