# CLAUDE.md — AI Assistant Guide for service_oper_uchet

This file provides context for AI assistants (Claude and others) working in this codebase.

---

## Project Overview

**service_oper_uchet** is an enterprise data synchronization system for operational accounting.
Its primary function is automatic synchronization of sales data parsed from Excel files into a
PostgreSQL database, using an Event Sourcing + CQRS architecture.

**Status:** Production-ready (v0.1.0, MIT license)

---

## Architecture

The project follows **Domain-Driven Design (DDD)** with three strict layers:

```
src/
├── domain/          # Business logic — NO external dependencies
│   ├── models/      # Core aggregates (Deal, DealItem, SyncSession, ExcelFile)
│   ├── value_objects/  # Immutable types (Money, Money5, Period, Status, HashKey)
│   ├── exceptions/  # Domain exceptions
│   ├── interfaces/  # Repository contracts (ABCs)
│   └── builders/    # Aggregate builders (DealBuilder)
├── application/     # Use cases — depends only on domain
│   ├── excel_parser/       # Excel parsing service
│   ├── change_detector/    # Detects new/changed/deleted deals
│   ├── data_validator/     # Validates parsed data
│   └── sync_orchestrator/  # Main synchronization workflow
└── infrastructure/  # External I/O — depends on domain + application
    ├── database/    # SQLAlchemy models and repository implementations
    ├── file_system/ # File I/O (aiofiles)
    ├── scheduler/   # APScheduler task scheduling
    ├── mappers/     # Domain ↔ DB model mapping
    └── workers/     # Background workers (ReadModelBuilder, PositionSync)
```

### Event Sourcing + CQRS

- **Write side:** All state changes are persisted as events in `event_store` table (JSONB)
- **Read side:** Denormalized `read_deals`, `read_positions`, `read_audit`, `read_stats` tables rebuilt by `ReadModelBuilder`
- **Snapshots:** `db_snapshots` table stores health metrics for monitoring

**Rule:** Never write directly to read model tables from domain/application code. Only `ReadModelBuilder` (infrastructure/workers) updates read models by processing events.

---

## Technology Stack

| Category | Technology |
|---|---|
| Language | Python 3.9–3.12 |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy v2 (async) |
| Migrations | Alembic |
| Data processing | Pandas v2, NumPy, OpenPyXL, XLCalculator |
| Async I/O | asyncpg, aiosqlite, aiofiles, aiohttp |
| Scheduling | APScheduler v3 |
| Caching | Redis v5 |
| Logging | Loguru |
| Retry logic | Tenacity |
| Monitoring | psutil |
| Testing | pytest, pytest-asyncio |
| Linting | Ruff, Black, MyPy |
| DB (prod) | PostgreSQL 16+ |
| DB (dev/test) | SQLite 3.35+ |

---

## Directory Structure

```
service_oper_uchet/
├── src/                    # Main application (see Architecture above)
├── migrations/             # Alembic migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/           # 0001–0005 migration scripts
├── tests/
│   ├── unit/               # Fast isolated tests
│   ├── integration/        # DB + multi-component tests
│   └── new/                # Recent test additions
├── testing/
│   └── scripts/            # Manual integration/connectivity scripts
├── dashboard/              # Monitoring and reporting tools
│   ├── generate_dashboard.py
│   ├── create_db_snapshot.py
│   ├── run_dashboard_check.py
│   ├── db_snapshot_service.py
│   └── excel_audit/
├── docs/                   # Architecture docs (DATABASE_DESIGN.md, etc.)
├── project_progress/       # Dev journal and status tracking
├── config.env              # Runtime configuration (committed defaults)
├── .env                    # Local overrides (git-ignored, never commit)
├── pyproject.toml          # Project metadata, deps, tool config
├── requirements.txt        # Pip-installable deps
├── docker-compose.db.yml   # PostgreSQL 16 container
└── run_migrations.sh       # Migration runner script
```

---

## Key Entry Points

| Purpose | Location |
|---|---|
| Main sync workflow | `src/application/sync_orchestrator/orchestrator.py` → `SyncOrchestratorService.execute_sync()` |
| Excel parsing | `src/application/excel_parser/` → `ExcelParserService.parse_file()` |
| Event processing | `src/infrastructure/workers/read_model_builder.py` → `ReadModelBuilder.process_latest_events()` |
| Position sync | `src/infrastructure/workers/position_sync_worker.py` |
| DB snapshots | `dashboard/db_snapshot_service.py` |
| HTML dashboard | `dashboard/generate_dashboard.py` |
| Integration test | `testing/scripts/test_sync_integration.py` |

---

## Database Schema

### Write Side
- **`event_store`** — Append-only event log. Fields: `event_id`, `aggregate_id`, `event_type`, `event_data` (JSONB), `metadata`, `sequence_number`, `created_at`, `processed_at`.

### Read Side (CQRS)
- **`read_deals`** — Denormalized deal view with financial summaries, `has_totals_error` quality flag.
- **`read_positions`** — Individual line items with `NUMERIC(18,5)` precision for prices and margins.
- **`read_audit`** — Full change history: `entity_type`, `entity_id`, `change_type`, `field_name`, `old_value`, `new_value`.
- **`read_stats`** — Period-aggregated statistics.

### Monitoring
- **`db_snapshot_deal_periods`** / **`db_snapshot_position_periods`** — Health metrics with 28 checks.

### Migration History
| Version | Description |
|---|---|
| 0001 | Initial event store + read models |
| 0002 | Added `hash_deal_key` for performance |
| 0003 | Increased purchase price/margin precision to NUMERIC(18,5) |
| 0004 | Removed versioning complexity from positions |
| 0005 | Added `db_snapshots` monitoring tables |

---

## Value Objects (Domain)

Always use value objects from `src/domain/value_objects/` for monetary amounts and periods:

| Type | Description |
|---|---|
| `Money` | Positive only, 2 decimal places |
| `Money5` | Positive only, 5 decimal places |
| `SignedMoney` | Positive or negative, 2 decimal places |
| `SignedMoney5` | Positive or negative, 5 decimal places |
| `Period` | Month + year period |
| `Status` | Enumerated status |
| `HashKey` | Hash-based unique key |

---

## Development Conventions

### Code Style
- **Python 3.9+** compatible syntax
- **Type hints** are mandatory for all function signatures
- **Pydantic v2** for data models and settings
- **Ruff** for linting (configured in `pyproject.toml`)
- **Black** for formatting
- **MyPy** for static type checking
- Async/await throughout — avoid blocking I/O in async code

### Layer Rules
1. `domain/` must have **zero imports** from `application/` or `infrastructure/`
2. `application/` may import from `domain/` only
3. `infrastructure/` may import from both `domain/` and `application/`
4. Cross-layer communication via interfaces defined in `domain/interfaces/`

### Error Handling
- Domain exceptions live in `src/domain/exceptions/`
- Use `Tenacity` for retry logic on external I/O (DB, file system)
- Use `Loguru` for all logging (`from loguru import logger`)

### Decimal / Monetary Precision
- Always use Python `Decimal` (not `float`) for money values
- Use safe parsing helpers — never `Decimal(str(value))` without validation
- Match the DB column precision (NUMERIC 18,2 vs 18,5) to the value object type

### String Fields
- Apply truncation validators based on DB column `max_length` before persistence
- Never silently truncate; log a warning if truncation occurs

---

## Configuration

Primary configuration is in `config.env` (committed defaults). Override with `.env` (local, git-ignored).

### Key Environment Variables

```bash
# Database
DB_TYPE=postgresql          # postgresql | sqlite
DB_HOST=so_pg
DB_PORT=5432
DB_NAME=so_uchet
DB_USER=so_user
DB_PASSWORD=so_pass
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_CONNECT_TIMEOUT=10
DB_QUERY_TIMEOUT=60

# Event Store
EVENT_STORE_PARTITION_MONTHS=12
EVENT_STORE_RETENTION_MONTHS=24

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Excel Parser
EXCEL_PARSER_CACHE_MODE=cache_only   # cache_only | no_cache | hybrid
EXCEL_PARSER_PRECALC_MODE=off        # off | on
EXCEL_PARSER_PRECALC_TIMEOUT_SEC=120
EXCEL_PARSER_PRECALC_TTL_DAYS=7
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit/

# Integration tests (requires DB)
pytest tests/integration/ -m integration_db

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific test file
pytest tests/unit/test_models.py -v
```

### Coverage Requirements
- **Overall minimum:** 85%
- **Critical components** (`domain/`, `application/`): 95%+

### Test Markers
- `unit` — isolated, no external dependencies
- `integration` — multi-component
- `integration_db` — requires a running database
- `e2e` — full end-to-end workflows
- `slow` — may be skipped in fast CI runs

### Manual Integration Scripts
Located in `testing/scripts/`:
- `test_sync_integration.py` — Full sync workflow
- `test_excel_parsing.py` — Excel parser only
- `test_postgres_connection.py` — DB connectivity check

---

## Database Operations

### Starting PostgreSQL (Docker)

```bash
docker-compose -f docker-compose.db.yml up -d
```

### Running Migrations

```bash
./run_migrations.sh
# or
cd migrations && alembic upgrade head
```

### Creating a New Migration

```bash
cd migrations && alembic revision --autogenerate -m "describe_change"
```

### Monitoring Dashboard

```bash
# Full before/after comparison workflow
python dashboard/run_dashboard_check.py

# Create a snapshot
python dashboard/create_db_snapshot.py

# Generate HTML report
python dashboard/generate_dashboard.py
```

---

## Performance Characteristics

| Operation | Throughput |
|---|---|
| Excel parsing | 1,000+ rows/second |
| Synchronization | 100+ deals/second |
| Change detection | 500+ entities/second |
| Full sync | < 15 minutes |
| Incremental sync | < 3 minutes |

---

## Documentation Index

| File | Content |
|---|---|
| `README.md` | Project overview and quick start |
| `docs/DEVELOPMENT_GUIDE.md` | Dev environment setup, standards, debugging |
| `docs/DATABASE_DESIGN.md` | Schema, event types, money precision |
| `docs/DATABASE_MANAGEMENT.md` | DB setup and connection pooling |
| `docs/MIGRATION_COMMANDS.md` | Alembic command reference |
| `project_progress/SYNC_FLOW.md` | Detailed sync workflow walkthrough |
| `project_progress/STATUS.md` | Current project status and milestones |

---

## Common Pitfalls to Avoid

1. **Do not use `float` for money.** Always use `Decimal` and the appropriate value object.
2. **Do not write directly to read model tables.** All writes go through the event store; read models are rebuilt by `ReadModelBuilder`.
3. **Do not add blocking I/O in async functions.** Use `aiofiles`, `asyncpg`, etc.
4. **Do not skip layer boundaries.** Infrastructure code must not be imported into `domain/`.
5. **Do not commit `.env` files.** Use `config.env` for committed defaults only.
6. **Do not add migrations without testing rollback.** Test both `upgrade` and `downgrade` steps.
7. **Do not use `str(float_value)` for Decimal conversion.** Use safe parsing utilities in the codebase.

---

## Branch & Commit Conventions

- Feature branches: `feature/<short-description>`
- Fix branches: `fix/<short-description>`
- Claude AI branches: `claude/<task-description>-<session-id>`
- Commit messages: imperative mood, concise, e.g. `Add safe decimal parser for purchase price`
- Never force-push to `master`
