# Ревью SYNC_ANALYSIS_PLAN — GPT Codex

**Дата:** 29 ноября 2025  
**Автор:** GPT-5.1 Codex  
**Цель:** Зафиксировать полный объем собранной информации по анализу системы синхронизации, чтобы разработчики могли продолжить работу без потери контекста.

---

## 1. Контекст проекта
- Архитектура DDD (domain/application/infrastructure/presentation).
- Основной поток: Excel → ChangeDetector → EventStore → ReadModelBuilder → read_deals/read_positions.
- Состояние синхронизации описано в `project_progress/SYNC_ANALYSIS_PLAN/SYNC_ANALYSIS_PLAN.md`; текущий прогресс задокументирован в `STATUS.md` и `DEVELOPMENT_JOURNAL.md`.

---

## 2. Методика ревью
1. Изучение обзорных документов (`PROJECT_OVERVIEW.md`, `STATUS.md`, `DEVELOPMENT_JOURNAL.md`) для фиксации архитектурных принципов.
2. Чтение плана `SYNC_ANALYSIS_PLAN.md` и проверка каждого утверждения на исходном коде.
3. Анализ исходников:
   - `src/application/change_detector/detector.py`
   - `src/infrastructure/workers/read_model_builder.py`
   - `src/infrastructure/database/repositories.py`
   - `src/infrastructure/workers/simple_position_sync.py`
4. Сопоставление найденных артефактов с приоритетами плана, формирование вариантов действий и перечня тестов.

---

## 3. Подтвержденные баги плана

| ID | Суть | Файл/фрагмент | Статус |
|----|------|---------------|--------|
| BUG-001 | `_create_audit_entry` завершает функцию до создания `ReadModelAudit`, таблица `read_audit` всегда пустая | `src/infrastructure/workers/read_model_builder.py` (строки 1218-1240) | Подтвержден |
| BUG-002 | `_recalculate_totals` трактует `NULL` totals как `0`, что вызывает ложные `has_totals_error` | `src/infrastructure/workers/read_model_builder.py` (строки 1182-1203) | Подтвержден |
| BUG-003 | При загрузке Deal через `_read_model_to_domain` `deal_key` пересоздается, возможен дрейф ключа и повторные INSERT | `src/infrastructure/database/repositories.py` (строки 244-284) | Требует доп. диагностики |

---

## 4. Дополнительные риски и пробелы

| GAP | Описание | Последствия |
|-----|----------|-------------|
| GAP-001 | `SimplePositionSync._upsert_position` выполняет `commit()` для каждой позиции | Потеря транзакционной целостности и деградация производительности |
| GAP-002 | `ChangeDetector` фактически сравнивает `deal_key`, а не `hash_deal_key`, т.к. репозиторий не возвращает `_hash_deal_key` | Возможны ложные INSERT при расхождениях в нормализации строк |
| GAP-003 | Отсутствует автоматизированный тест сценария восстановления `read_audit` | Риск регресса после правок |
| GAP-004 | `find_by_period` сравнивает «сырые» строки `period_month/year`; расхождение в нормализации (локаль, регистр) приводит к пустым выборкам | ChangeDetector видит пустую БД → все сделки как INSERT |
| GAP-005 | Нет ограничений на повторную генерацию событий при повторных синхронизациях | Рост Event Store и увеличение времени `process_latest_events` |

---

## 5. Рекомендованные варианты действий

### Вариант A — Минимально достаточный фикс
- Удалить `return` в `_create_audit_entry`.
- Исправить логику `has_totals_error` (не сравнивать `None`).
- Добавить временный лог сравнения `deal_key` из БД и Excel.
- **Плюсы:** быстрый эффект.
- **Минусы:** не решает транзакционные и тестовые пробелы.

### Вариант B — Стабилизация контура Read Model (рекомендую)
- Вариант A +
  - Переписать `_recalculate_totals` под доменную логику (`None` → отсутствие данных).
  - Вернуть полноценное создание `ReadModelAudit` и покрыть тестами.
  - Убрать `commit()` из `_upsert_position`, оставить контроль транзакций на оркестратор.
  - Добавить unit-тесты для totals/audit, интеграционные проверки повторной синхронизации.
- **Плюсы:** закрывает основные риски (BUG-001/002, GAP-001/003).
- **Минусы:** 3–4 дня работы + регрессия.

### Вариант C — Расширенный аудит Change Detection
- Вариант B +
  - Диагностировать `_read_model_to_domain`, обеспечить строгий паритет `deal_key`.
  - Ввести механизм детерминированного сравнения `hash_deal_key`.
  - Выполнить нагрузочные тесты Event Store и внедрить метрики.
- **Плюсы:** устраняет первопричины избыточных событий, готовит систему к масштабированию.
- **Минусы:** неделя+ работы, требуется тестовый стенд с реальными данными.

---

## 6. Предлагаемые тесты и проверки
1. **Unit:** `_create_audit_entry` (успешная запись, обработка ошибок) и `_recalculate_totals` (кейсы `all NULL`, `partial NULL`, `mismatch`).
2. **Integration:** двойной запуск синхронизации одним и тем же файлом; ожидаем отсутствие новых `DealCreated`.
3. **Performance:** сравнение времени `SimplePositionSync` до/после удаления частых `commit()` на файлах с 1000+ позиций.
4. **SQL-проверки:** скрипты из приложения B плана + запрос на сопоставление `read_deals.deal_key` с `Deal.deal_key`.

---

## 7. Следующие шаги
1. Утвердить вариант реализации (A/B/C). Рекомендую стартовать с варианта B.
2. Подготовить задачи в трекере:
   - BUG-001/002 фиксы + тесты.
   - Снятие `commit()` в `SimplePositionSync`.
   - Диагностика `deal_key` (логирование + debug-скрипт).
3. Обновить `DEVELOPMENT_JOURNAL.md` и `STATUS.md` после выполнения каждого шага.
4. Создать debug-скрипт в `scripts/debug/compare_deal_keys.py` для сравнения ключей Excel/БД.

---

## 8. Ссылки на исходные документы
- План анализа: `project_progress/SYNC_ANALYSIS_PLAN/SYNC_ANALYSIS_PLAN.md`
- Обзор ревью: `project_progress/SYNC_ANALYSIS_PLAN/ARCHITECT_REVIEW_2025-11-29.md`
- Журнал хронологии: `project_progress/DEVELOPMENT_JOURNAL.md`
- Текущий статус: `project_progress/STATUS.md`

Документ предназначен для быстрой загрузки контекста сторонним разработчиком и может использоваться как единая точка входа в ревью SYNC-подсистемы.
