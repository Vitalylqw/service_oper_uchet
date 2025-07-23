"""
Scheduler Infrastructure - автоматические задачи синхронизации.

Содержит:
- config: Конфигурация планировщика (APScheduler + Windows Task Scheduler)
- service: Основной сервис планирования с retry логикой
- models: Модели для результатов планирования
- jobs: Определения задач синхронизации

Технологии: APScheduler, tenacity (retry), Windows Task Scheduler (резерв)
"""

from .config import SchedulerConfig
from .models import (
    JobExecutionResult,
    JobExecutionStatus,
    JobScheduleInfo,
    SchedulerMetrics,
    SchedulerState,
    SyncJobType,
)
from .service import SchedulerService

__all__ = [
    "SchedulerConfig",
    "SchedulerService",
    "JobExecutionResult",
    "JobExecutionStatus",
    "JobScheduleInfo",
    "SchedulerMetrics",
    "SchedulerState",
    "SyncJobType",
]
