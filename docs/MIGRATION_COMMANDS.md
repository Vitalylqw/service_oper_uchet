# Команды миграций

## Назначение

Этот документ содержит рабочие команды Alembic для текущего состояния репозитория. Он не описывает
исторические эксперименты со структурой миграций.

## Текущая модель истории

- активная история Alembic состоит из двух ревизий в `migrations/versions/`:
  `0001_baseline_current_schema.py` и `0002_drop_read_audit.py`;
- предыдущая цепочка `0001..0005` сохранена в `migrations/archive/versions_pre_baseline_20260308/`;
- для существующей БД с данными нельзя полагаться на старую историю ревизий, используется
  проверка схемы и затем `stamp`.

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

### Существующая legacy-БД после перехода на baseline

Проверить готовность схемы:

```bash
python scripts/services/align_existing_db_to_baseline.py
```

Применить известные безопасные исправления и затем привязать baseline:

```bash
python scripts/services/align_existing_db_to_baseline.py --apply-known-fixes --stamp
```

Windows:

```bat
scripts\\services\\align_existing_db_to_baseline.bat --apply-known-fixes --stamp
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
- `stamp` допустим только после проверки, что существующая БД соответствует baseline-контракту;
- helper-скрипт для выравнивания existing DB исправляет только известные и проверенные расхождения;
- после `stamp` всё равно нужно довести БД до `head`, чтобы применилась миграция `0002` и
  legacy-таблица `read_audit` была удалена из active schema;
- описание миграции должно отражать причину изменения, а не только механическое действие;
- после миграции нужно проверить не только схему, но и рабочие сценарии sync flow.

## Что считать источником истины

Каноника по миграциям определяется комбинацией:

- `migrations/versions/*.py`
- `migrations/archive/versions_pre_baseline_20260308/` как historical memory, но не active history;
- `migrations/env.py`
- `src/infrastructure/database/models.py`

Если старый документ по миграциям противоречит этим файлам, ориентироваться нужно на код и текущие
ревизии Alembic.






