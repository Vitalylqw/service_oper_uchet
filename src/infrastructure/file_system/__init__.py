"""
File System Infrastructure - получение файлов из различных источников.

Содержит:
- config: Конфигурация для различных протоколов (SMB/CIFS, FTP, SFTP, HTTP)
- service: Основной сервис получения файлов с мониторингом изменений
- protocols: Реализации протоколов для получения файлов
- models: Модели для результатов получения файлов

Технологии: SMB/CIFS, FTP, SFTP, HTTP, file monitoring
"""

from .config import FileSystemConfig
from .models import (
    FileChangeType,
    FileInfo,
    FileMonitoringState,
    FileOperationStatus,
    FileRetrievalResult,
    FileSystemMetrics,
    FileValidationResult,
    ProtocolCapabilities,
)
from .service import FileSystemService

__all__ = [
    "FileSystemConfig",
    "FileSystemService",
    "FileChangeType",
    "FileInfo",
    "FileMonitoringState",
    "FileOperationStatus",
    "FileRetrievalResult",
    "FileSystemMetrics",
    "FileValidationResult",
    "ProtocolCapabilities",
]
