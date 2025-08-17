"""
Domain модели системы.

Содержит основные сущности:
- Deal: Сделка с клиентом
- DealItem: Позиция товара в сделке
- SyncSession: Сессия синхронизации
- ExcelFile: Модель Excel файла для валидации
- ExcelSheet: Модель листа Excel для валидации
"""

from .deal import Deal, DealItem
from .excel_file import ExcelFile, ExcelSheet, FileValidationStatus, SheetValidationStatus
from .sync_session import SyncSession, SyncType

__all__ = [
    "Deal", "DealItem", "SyncSession", "SyncType",
    "ExcelFile", "ExcelSheet", "FileValidationStatus", "SheetValidationStatus"
] 