"""
Excel File domain models.

Contains models for Excel file validation and sheet structure validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4
import os

from pydantic import BaseModel, Field, computed_field, field_validator, ConfigDict

from ..value_objects import HashKey


class FileValidationStatus(str, Enum):
    """Status of file validation."""
    
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


class SheetValidationStatus(str, Enum):
    """Status of sheet validation."""
    
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    SKIPPED = "skipped"
    ERROR = "error"


class PeriodValidation(BaseModel):
    """Валидация периода из названия листа."""
    
    extracted_month: Optional[str] = Field(None, description="Извлеченный месяц")
    extracted_year: Optional[str] = Field(None, description="Извлеченный год")
    is_valid_format: bool = Field(default=False, description="Правильный формат")
    is_valid_period: bool = Field(default=False, description="Валидный период")
    expected_period: Optional[str] = Field(None, description="Ожидаемый период")
    validation_error: Optional[str] = Field(None, description="Ошибка валидации")


class BusinessRulesValidation(BaseModel):
    """Валидация бизнес-правил."""
    
    has_client_data: bool = Field(default=False, description="Есть данные о клиентах")
    has_invoice_data: bool = Field(default=False, description="Есть данные о счетах")
    has_product_data: bool = Field(default=False, description="Есть данные о товарах")
    has_financial_data: bool = Field(default=False, description="Есть финансовые данные")
    rules_violations: list[str] = Field(default_factory=list, description="Нарушения правил")


class FinancialValidation(BaseModel):
    """Валидация финансовых данных."""
    
    revenue_sum: Optional[float] = Field(None, description="Сумма выручки")
    margin_sum: Optional[float] = Field(None, description="Сумма маржи")
    cost_sum: Optional[float] = Field(None, description="Сумма затрат")
    financial_consistency: bool = Field(default=False, description="Финансовая согласованность")
    financial_errors: list[str] = Field(default_factory=list, description="Финансовые ошибки")


class FileMonitoringInfo(BaseModel):
    """Информация о мониторинге файла."""
    
    is_monitored: bool = Field(default=False, description="Файл мониторится")
    monitoring_started: Optional[datetime] = Field(None, description="Начало мониторинга")
    last_check: Optional[datetime] = Field(None, description="Последняя проверка")
    change_count: int = Field(default=0, description="Количество изменений")
    monitoring_status: str = Field(default="unknown", description="Статус мониторинга")


class ExcelSheet(BaseModel):
    """Excel sheet validation model."""
    
    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True
    )
    
    # Идентификаторы
    id: UUID = Field(default_factory=uuid4, description="Уникальный ID листа")
    file_id: Optional[UUID] = Field(None, description="ID родительского файла")
    
    # Основная информация
    name: str = Field(..., min_length=1, max_length=100, description="Название листа")
    index: int = Field(..., ge=0, description="Индекс листа в файле")
    
    # Валидация
    status: SheetValidationStatus = Field(
        default=SheetValidationStatus.PENDING, 
        description="Статус валидации листа"
    )
    is_required: bool = Field(default=False, description="Обязательный лист")
    is_processed: bool = Field(default=False, description="Лист обрабатывается")
    
    # Структура данных
    header_row: Optional[int] = Field(None, ge=0, description="Номер строки с заголовками")
    data_start_row: Optional[int] = Field(None, ge=0, description="Номер строки начала данных")
    total_rows: int = Field(default=0, description="Общее количество строк")
    total_columns: int = Field(default=0, description="Общее количество колонок")
    
    # Заголовки
    expected_headers: list[str] = Field(
        default_factory=list, 
        description="Ожидаемые заголовки"
    )
    actual_headers: list[str] = Field(
        default_factory=list, 
        description="Фактические заголовки"
    )
    missing_headers: list[str] = Field(
        default_factory=list, 
        description="Отсутствующие заголовки"
    )
    extra_headers: list[str] = Field(
        default_factory=list, 
        description="Лишние заголовки"
    )
    
    # Валидация данных
    has_data: bool = Field(default=False, description="Есть ли данные в листе")
    is_empty: bool = Field(default=True, description="Лист пустой")
    has_errors: bool = Field(default=False, description="Есть ошибки валидации")
    
    # НОВЫЕ ПОЛЯ: Валидация периода
    period_validation: Optional[PeriodValidation] = Field(
        None, 
        description="Валидация периода из названия листа"
    )
    expected_period_pattern: Optional[str] = Field(
        None, 
        description="Ожидаемый паттерн периода (например, 'Март 2025')"
    )
    period_is_valid: bool = Field(
        default=False, 
        description="Название листа соответствует ожидаемому периоду"
    )
    period_validation_error: Optional[str] = Field(
        None, 
        description="Ошибка валидации периода"
    )
    
    # НОВЫЕ ПОЛЯ: Бизнес-валидация
    business_rules_validation: Optional[BusinessRulesValidation] = Field(
        None, 
        description="Валидация бизнес-правил"
    )
    
    # НОВЫЕ ПОЛЯ: Финансовая валидация
    financial_validation: Optional[FinancialValidation] = Field(
        None, 
        description="Валидация финансовых данных"
    )
    
    # Ошибки и предупреждения
    validation_errors: list[str] = Field(
        default_factory=list, 
        description="Ошибки валидации"
    )
    validation_warnings: list[str] = Field(
        default_factory=list, 
        description="Предупреждения валидации"
    )
    
    # Метаданные
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    @computed_field
    @property
    def sheet_key(self) -> str:
        """Уникальный ключ листа."""
        return f"{self.name}|{self.index}"
    
    @computed_field
    @property
    def hash_key(self) -> HashKey:
        """Hash ключ для быстрого сравнения изменений."""
        data = {
            "name": self.name,
            "index": self.index,
            "header_row": self.header_row,
            "data_start_row": self.data_start_row,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "expected_headers": self.expected_headers,
            "actual_headers": self.actual_headers,
        }
        return HashKey.from_dict(data)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize sheet name."""
        return v.strip()
    
    @property
    def is_valid(self) -> bool:
        """Check if sheet is valid."""
        return (
            self.status == SheetValidationStatus.VALID and 
            not self.has_errors and
            self.has_data and
            self.period_is_valid
        )
    
    @property
    def validation_summary(self) -> str:
        """Get validation summary."""
        if self.is_valid:
            warning_text = f", {len(self.validation_warnings)} предупреждений" if self.validation_warnings else ""
            return f"Лист '{self.name}' валиден{warning_text}"
        else:
            return (
                f"Лист '{self.name}' невалиден: "
                f"{len(self.validation_errors)} ошибок, "
                f"{len(self.validation_warnings)} предупреждений"
            )
    
    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.validation_errors.append(error)
        self.has_errors = True
        self.status = SheetValidationStatus.INVALID
        self.updated_at = datetime.now()
    
    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.validation_warnings.append(warning)
        self.updated_at = datetime.now()
    
    def mark_valid(self) -> None:
        """Mark sheet as valid."""
        self.status = SheetValidationStatus.VALID
        self.has_errors = False
        self.updated_at = datetime.now()
    
    def mark_skipped(self) -> None:
        """Mark sheet as skipped."""
        self.status = SheetValidationStatus.SKIPPED
        self.updated_at = datetime.now()
    
    # НОВЫЕ МЕТОДЫ: Валидация периода
    def validate_sheet_period(self, expected_period: Optional[str] = None) -> None:
        """Validate sheet name contains valid period."""
        try:
            from domain.value_objects import Period
            
            # Extract period from sheet name
            period = Period.from_sheet_name(self.name)
            
            # Create period validation
            self.period_validation = PeriodValidation(
                extracted_month=period.month,
                extracted_year=period.year,
                is_valid_format=True,
                is_valid_period=True,
                expected_period=expected_period
            )
            
            # Check if period matches expected
            if expected_period and str(period) != expected_period:
                self.period_validation.is_valid_period = False
                self.period_validation.validation_error = f"Ожидался период {expected_period}, получен {period}"
                self.add_error(f"Несоответствие периода: ожидался {expected_period}, получен {period}")
            else:
                self.period_is_valid = True
                
        except ValueError as e:
            self.period_validation = PeriodValidation(
                is_valid_format=False,
                is_valid_period=False,
                validation_error=str(e)
            )
            self.add_error(f"Ошибка валидации периода: {str(e)}")
    
    # НОВЫЕ МЕТОДЫ: Бизнес-валидация
    def validate_business_rules(self, config: Any) -> None:
        """Validate business rules for sheet."""
        self.business_rules_validation = BusinessRulesValidation()
        
        # Check for required data
        if hasattr(config, 'require_client_data') and config.require_client_data:
            if "Клиент" not in self.actual_headers:
                self.business_rules_validation.rules_violations.append("Отсутствует колонка 'Клиент'")
                self.business_rules_validation.has_client_data = False
            else:
                self.business_rules_validation.has_client_data = True
        
        if hasattr(config, 'require_invoice_data') and config.require_invoice_data:
            invoice_headers = ["Счет", "Номер счета", "Дата счета"]
            found_invoice_headers = [h for h in invoice_headers if h in self.actual_headers]
            if not found_invoice_headers:
                self.business_rules_validation.rules_violations.append("Отсутствуют данные о счетах")
                self.business_rules_validation.has_invoice_data = False
            else:
                self.business_rules_validation.has_invoice_data = True
        
        if hasattr(config, 'require_financial_data') and config.require_financial_data:
            financial_headers = ["Выручка", "Маржа", "Стоимость"]
            found_financial_headers = [h for h in financial_headers if h in self.actual_headers]
            if not found_financial_headers:
                self.business_rules_validation.rules_violations.append("Отсутствуют финансовые данные")
                self.business_rules_validation.has_financial_data = False
            else:
                self.business_rules_validation.has_financial_data = True
        
        # Add violations as errors
        for violation in self.business_rules_validation.rules_violations:
            self.add_error(violation)


class ExcelFile(BaseModel):
    """Excel file validation model."""
    
    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True
    )
    
    # Идентификаторы
    id: UUID = Field(default_factory=uuid4, description="Уникальный ID файла")
    
    # Основная информация
    file_path: str = Field(..., description="Путь к файлу")
    file_name: str = Field(..., min_length=1, max_length=255, description="Название файла")
    file_extension: str = Field(..., description="Расширение файла")
    file_size: int = Field(..., ge=0, description="Размер файла в байтах")
    file_hash: str = Field(..., description="Hash файла для проверки целостности")
    
    # Валидация файла
    status: FileValidationStatus = Field(
        default=FileValidationStatus.PENDING, 
        description="Статус валидации файла"
    )
    is_valid: bool = Field(default=False, description="Файл валиден")
    
    # Структура файла
    total_sheets: int = Field(default=0, description="Общее количество листов")
    valid_sheets: int = Field(default=0, description="Количество валидных листов")
    invalid_sheets: int = Field(default=0, description="Количество невалидных листов")
    skipped_sheets: int = Field(default=0, description="Количество пропущенных листов")
    
    # Листы
    sheets: list[ExcelSheet] = Field(
        default_factory=list, 
        description="Список листов в файле"
    )
    required_sheets: list[str] = Field(
        default_factory=list, 
        description="Список обязательных листов"
    )
    allowed_sheets: list[str] = Field(
        default_factory=list, 
        description="Список разрешенных листов"
    )
    
    # Валидация названия файла
    name_pattern: Optional[str] = Field(
        None, 
        description="Регулярное выражение для валидации названия файла"
    )
    name_is_valid: bool = Field(default=False, description="Название файла валидно")
    name_validation_error: Optional[str] = Field(
        None, 
        description="Ошибка валидации названия файла"
    )
    
    # НОВЫЕ ПОЛЯ: Валидация пути к файлу
    source_directory: Optional[str] = Field(
        None, 
        description="Ожидаемая исходная директория"
    )
    path_is_valid: bool = Field(
        default=False, 
        description="Файл находится в правильной директории"
    )
    path_validation_error: Optional[str] = Field(
        None, 
        description="Ошибка валидации пути"
    )
    
    # НОВЫЕ ПОЛЯ: Информация о источнике файла
    file_source: Optional[str] = Field(
        None, 
        description="Источник файла (local, smb, ftp, etc.)"
    )
    original_path: Optional[str] = Field(
        None, 
        description="Оригинальный путь к файлу"
    )
    
    # НОВЫЕ ПОЛЯ: Интеграция с мониторингом
    monitoring_info: Optional[FileMonitoringInfo] = Field(
        None, 
        description="Информация о мониторинге файла"
    )
    last_modified: Optional[datetime] = Field(
        None, 
        description="Время последнего изменения"
    )
    change_detected: bool = Field(
        default=False, 
        description="Обнаружены изменения"
    )
    
    # Ошибки и предупреждения
    validation_errors: list[str] = Field(
        default_factory=list, 
        description="Ошибки валидации файла"
    )
    validation_warnings: list[str] = Field(
        default_factory=list, 
        description="Предупреждения валидации файла"
    )
    
    # Метаданные
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    
    @computed_field
    @property
    def file_key(self) -> str:
        """Уникальный ключ файла."""
        return f"{self.file_name}|{self.file_hash[:8]}"
    
    @computed_field
    @property
    def hash_key(self) -> HashKey:
        """Hash ключ для быстрого сравнения изменений."""
        data = {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "total_sheets": self.total_sheets,
            "required_sheets": self.required_sheets,
            "allowed_sheets": self.allowed_sheets,
        }
        return HashKey.from_dict(data)
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"File does not exist: {v}")
        return str(path.absolute())
    
    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Validate and normalize file name."""
        return v.strip()
    
    @property
    def validation_summary(self) -> str:
        """Get validation summary."""
        if self.is_valid:
            warning_text = f", {len(self.validation_warnings)} предупреждений" if self.validation_warnings else ""
            return f"Файл '{self.file_name}' валиден{warning_text}"
        else:
            return (
                f"Файл '{self.file_name}' невалиден: "
                f"{len(self.validation_errors)} ошибок, "
                f"{len(self.validation_warnings)} предупреждений"
            )
    
    @property
    def success_rate(self) -> float:
        """Success rate for file validation."""
        if self.total_sheets == 0:
            return 0.0
        return (self.valid_sheets / self.total_sheets) * 100
    
    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.validation_errors.append(error)
        self.is_valid = False
        self.status = FileValidationStatus.INVALID
        self.updated_at = datetime.now()
    
    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.validation_warnings.append(warning)
        self.updated_at = datetime.now()
    
    def mark_valid(self) -> None:
        """Mark file as valid."""
        self.is_valid = True
        self.status = FileValidationStatus.VALID
        self.validated_at = datetime.now()
        self.updated_at = datetime.now()
    
    def get_sheet_by_name(self, name: str) -> Optional[ExcelSheet]:
        """Get sheet by name."""
        for sheet in self.sheets:
            if sheet.name.lower() == name.lower():
                return sheet
        return None
    
    def get_valid_sheets(self) -> list[ExcelSheet]:
        """Get all valid sheets."""
        return [sheet for sheet in self.sheets if sheet.is_valid]
    
    def get_required_sheets(self) -> list[ExcelSheet]:
        """Get all required sheets."""
        return [sheet for sheet in self.sheets if sheet.is_required]
    
    def get_missing_required_sheets(self) -> list[str]:
        """Get missing required sheets."""
        found_sheets = {sheet.name.lower() for sheet in self.sheets}
        return [
            required for required in self.required_sheets 
            if required.lower() not in found_sheets
        ]
    
    def update_sheet_stats(self) -> None:
        """Update sheet statistics."""
        self.valid_sheets = len([s for s in self.sheets if s.is_valid])
        self.invalid_sheets = len([s for s in self.sheets if s.status == SheetValidationStatus.INVALID])
        self.skipped_sheets = len([s for s in self.sheets if s.status == SheetValidationStatus.SKIPPED])
        self.updated_at = datetime.now()
    
    # НОВЫЕ МЕТОДЫ: Валидация пути к файлу
    def validate_file_location(self, expected_source_directory: Optional[str] = None) -> None:
        """Validate file path and location."""
        try:
            file_path = Path(self.file_path)
            
            # Check if file is in expected directory
            if expected_source_directory:
                expected_path = Path(expected_source_directory)
                if not file_path.is_relative_to(expected_path):
                    self.path_is_valid = False
                    self.path_validation_error = f"Файл должен находиться в директории {expected_source_directory}"
                    self.add_error(self.path_validation_error)
                else:
                    self.path_is_valid = True
                    self.source_directory = str(expected_path)
            
            # Check file accessibility
            if not file_path.exists():
                self.add_error(f"Файл не существует: {self.file_path}")
            elif not file_path.is_file():
                self.add_error(f"Путь не является файлом: {self.file_path}")
            elif not os.access(file_path, os.R_OK):
                self.add_error(f"Файл недоступен для чтения: {self.file_path}")
                
        except Exception as e:
            self.add_error(f"Ошибка валидации пути: {str(e)}")
    
    # НОВЫЕ МЕТОДЫ: Валидация периодов всех листов
    def validate_all_sheet_periods(self, expected_periods: Optional[list[str]] = None) -> None:
        """Validate periods for all sheets."""
        for sheet in self.sheets:
            if sheet.is_processed:
                expected_period = None
                if expected_periods and len(expected_periods) > sheet.index:
                    expected_period = expected_periods[sheet.index]
                
                sheet.validate_sheet_period(expected_period)
        
        # Check if all sheets have valid periods
        invalid_period_sheets = [s for s in self.sheets if not s.period_is_valid and s.is_processed]
        if invalid_period_sheets:
            self.add_error(f"Листы с невалидными периодами: {[s.name for s in invalid_period_sheets]}")
    
    # НОВЫЕ МЕТОДЫ: Бизнес-валидация всех листов
    def validate_all_business_rules(self, config: Any) -> None:
        """Validate business rules for all sheets."""
        for sheet in self.sheets:
            if sheet.is_processed:
                sheet.validate_business_rules(config)
        
        # Check overall business rules compliance
        invalid_business_sheets = [s for s in self.sheets if s.business_rules_validation and s.business_rules_validation.rules_violations and s.is_processed]
        if invalid_business_sheets:
            self.add_error(f"Листы с нарушениями бизнес-правил: {[s.name for s in invalid_business_sheets]}")
    
    # НОВЫЕ МЕТОДЫ: Установка информации о мониторинге
    def set_monitoring_info(self, is_monitored: bool = True, monitoring_status: str = "active") -> None:
        """Set monitoring information for file."""
        self.monitoring_info = FileMonitoringInfo(
            is_monitored=is_monitored,
            monitoring_started=datetime.now() if is_monitored else None,
            monitoring_status=monitoring_status
        )
        self.updated_at = datetime.now()
    
    def update_monitoring_status(self, status: str, change_detected: bool = False) -> None:
        """Update monitoring status."""
        if self.monitoring_info:
            self.monitoring_info.monitoring_status = status
            self.monitoring_info.last_check = datetime.now()
            if change_detected:
                self.monitoring_info.change_count += 1
                self.change_detected = True
        self.updated_at = datetime.now() 