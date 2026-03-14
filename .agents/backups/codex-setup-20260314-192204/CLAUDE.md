# CLAUDE.md — service-oper-uchet

## Среда
- Ubuntu, devcontainer, VS Code + Claude Code

## Инженерные правила
@/home/vscode/.claude/ENGINEERING_RULES.md

## Цели и бизнес-логика проекта
@./project_goals.md

## Архитектура

- DDD: слои `domain`, `application`, `infrastructure` внутри `src/`
- Язык разработки: Python
- БД OSTGRESQL

### Правила импортов
- Между слоями внутри `src/` — относительные импорты  
  например: `from ..database.models import ReadModelPosition`
- Внутри одного слоя — абсолютные импорты  
  например: `from .models import SyncConfiguration`
- Вне `src/` (тесты, скрипты) — любые импорты


## Стандарты кода
- PEP8, максимальная длина строки — 100 символов
- Docstring: Google-стиль, на английском
- Типы: явные аннотации (PEP 484), `from __future__ import annotations`
- Inline-комментарии: только для нетривиальных участков
- Логирование: подробное, везде
- Если код уже существует — предлагай diff-patch
- Не галлюцинируй версии библиотек — проверяй `pyproject.toml`


## Инструменты
- Линтинг: `ruff check .`
- Git: Conventional Commits, semantic-release
- Язык коммитов и docstring: английский

## Документация проекта
@docs - описание и основные документы
@project_progress -  динамика проекта
    
