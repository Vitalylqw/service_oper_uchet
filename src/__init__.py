"""
Service Oper Uchet - система синхронизации данных Excel → PostgreSQL с версионностью.

Реализует Domain Driven Design (DDD) архитектуру:
- domain: предметная область
- application: бизнес-логика
- infrastructure: внешние интеграции
"""

__version__ = "0.1.0"

# Centralized imports to avoid import path issues
# Application layer
from .application.excel_parser import ExcelParserService
from .application.change_detector import ChangeDetectorService
from .application.sync_orchestrator import SyncOrchestratorService, SyncConfiguration, SyncResult, SyncSummary

# Infrastructure layer
from .infrastructure.workers.read_model_builder import ReadModelBuilder
from .infrastructure.database.connection import DatabaseConfig, DatabaseManager
from .infrastructure.database.event_store import EventStoreImplementation

from .infrastructure.database.repositories import (
    DealRepositoryImplementation,
    SyncSessionRepositoryImplementation,
)

# Domain layer
from .domain.models import Deal, DealItem
from .domain.value_objects import Money, Period, Status, SignedMoney

# Re-export commonly used components
__all__ = [
    # Application services
    "ExcelParserService",
    "ChangeDetectorService", 
    "SyncOrchestratorService",
    "SyncConfiguration",
    "SyncResult", 
    "SyncSummary",
    
    # Infrastructure components
    "ReadModelBuilder",
    "DatabaseConfig",
    "DatabaseManager",
    "EventStoreImplementation",
    "DealRepositoryImplementation",
    "SyncSessionRepositoryImplementation",
    
    # Domain models
    "Deal",
    "DealItem",
    "Money",
    "Period", 
    "Status",
    "SignedMoney",
]
