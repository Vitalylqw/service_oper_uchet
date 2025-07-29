"""
Configuration for Excel file validation.

Contains settings for file name validation, sheet validation, and data structure validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Pattern
import re

from pydantic import BaseModel, Field


class BusinessRulesConfig(BaseModel):
    """Конфигурация бизнес-правил."""
    
    require_client_data: bool = Field(default=True, description="Требовать данные о клиентах")
    require_invoice_data: bool = Field(default=True, description="Требовать данные о счетах")
    require_financial_data: bool = Field(default=True, description="Требовать финансовые данные")
    require_product_data: bool = Field(default=True, description="Требовать данные о товарах")
    validate_financial_consistency: bool = Field(default=True, description="Проверять финансовую согласованность")
    max_deals_per_sheet: Optional[int] = Field(None, description="Максимум сделок на лист")
    min_deals_per_sheet: int = Field(default=1, description="Минимум сделок на лист")


class PeriodValidationConfig(BaseModel):
    """Конфигурация валидации периодов."""
    
    require_period_in_sheet_name: bool = Field(default=True, description="Требовать период в названии листа")
    allowed_months: List[str] = Field(
        default_factory=lambda: [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ], 
        description="Разрешенные месяцы"
    )
    allowed_years: List[str] = Field(
        default_factory=lambda: [str(year) for year in range(2020, 2031)], 
        description="Разрешенные годы"
    )
    period_format_pattern: str = Field(
        default=r"^[А-Яа-я]+ \d{4}$", 
        description="Паттерн формата периода"
    )
    strict_period_validation: bool = Field(default=False, description="Строгая валидация периодов")
    allow_future_periods: bool = Field(default=False, description="Разрешить будущие периоды")


class FilePathValidationConfig(BaseModel):
    """Конфигурация валидации путей к файлам."""
    
    require_valid_source_directory: bool = Field(default=True, description="Требовать валидную исходную директорию")
    allowed_source_directories: List[str] = Field(
        default_factory=list, 
        description="Разрешенные исходные директории"
    )
    validate_file_accessibility: bool = Field(default=True, description="Проверять доступность файла")
    validate_file_permissions: bool = Field(default=True, description="Проверять права доступа к файлу")
    allow_network_paths: bool = Field(default=True, description="Разрешить сетевые пути")


class SheetConfig(BaseModel):
    """Configuration for Excel sheet validation."""
    
    name: str = Field(..., description="Sheet name pattern")
    is_required: bool = Field(default=False, description="Is sheet required")
    is_processed: bool = Field(default=True, description="Should sheet be processed")
    
    # Header validation
    expected_headers: List[str] = Field(
        default_factory=list, 
        description="Expected headers in sheet"
    )
    required_headers: List[str] = Field(
        default_factory=list, 
        description="Required headers (subset of expected)"
    )
    optional_headers: List[str] = Field(
        default_factory=list, 
        description="Optional headers"
    )
    
    # Data validation
    min_rows: int = Field(default=1, description="Minimum number of data rows")
    max_rows: Optional[int] = Field(None, description="Maximum number of data rows")
    min_columns: int = Field(default=1, description="Minimum number of columns")
    max_columns: Optional[int] = Field(None, description="Maximum number of columns")
    
    # Header row detection
    header_row_patterns: List[str] = Field(
        default_factory=list, 
        description="Patterns to identify header row"
    )
    max_header_search_rows: int = Field(
        default=10, 
        description="Maximum rows to search for header"
    )
    
    # Data structure
    data_start_offset: int = Field(
        default=1, 
        description="Rows offset from header to data start"
    )
    
    # Validation rules
    allow_empty: bool = Field(default=False, description="Allow empty sheets")
    allow_extra_headers: bool = Field(default=True, description="Allow extra headers")
    strict_header_match: bool = Field(default=False, description="Strict header matching")
    
    # НОВЫЕ ПОЛЯ: Бизнес-правила для листа
    business_rules: BusinessRulesConfig = Field(
        default_factory=BusinessRulesConfig,
        description="Бизнес-правила для листа"
    )
    
    # НОВЫЕ ПОЛЯ: Валидация периода для листа
    period_validation: PeriodValidationConfig = Field(
        default_factory=PeriodValidationConfig,
        description="Валидация периода для листа"
    )
    
    def matches_name(self, sheet_name: str) -> bool:
        """Check if sheet name matches pattern."""
        try:
            return bool(re.match(self.name, sheet_name, re.IGNORECASE))
        except re.error:
            return sheet_name.lower() == self.name.lower()
    
    def get_missing_required_headers(self, actual_headers: List[str]) -> List[str]:
        """Get missing required headers."""
        actual_lower = [h.lower().strip() for h in actual_headers]
        return [h for h in self.required_headers if h.lower().strip() not in actual_lower]
    
    def get_extra_headers(self, actual_headers: List[str]) -> List[str]:
        """Get extra headers not in expected list."""
        expected_lower = [h.lower().strip() for h in self.expected_headers]
        return [h for h in actual_headers if h.lower().strip() not in expected_lower]


class FileNameConfig(BaseModel):
    """Configuration for file name validation."""
    
    pattern: str = Field(
        default=r"^[a-zA-Z0-9_\-\s]+\.(xlsx|xls)$",
        description="Regex pattern for file name validation"
    )
    required_extensions: List[str] = Field(
        default_factory=lambda: [".xlsx", ".xls"],
        description="Required file extensions"
    )
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    min_file_size_kb: int = Field(default=1, description="Minimum file size in KB")
    
    def validate_name(self, file_name: str) -> bool:
        """Validate file name against pattern."""
        try:
            return bool(re.match(self.pattern, file_name))
        except re.error:
            return False
    
    def validate_extension(self, extension: str) -> bool:
        """Validate file extension."""
        return extension.lower() in [ext.lower() for ext in self.required_extensions]
    
    def validate_size(self, size_bytes: int) -> bool:
        """Validate file size."""
        min_size = self.min_file_size_kb * 1024
        max_size = self.max_file_size_mb * 1024 * 1024
        return min_size <= size_bytes <= max_size


class ExcelValidationConfig(BaseModel):
    """Main configuration for Excel validation."""
    
    # File validation
    file_name: FileNameConfig = Field(
        default=FileNameConfig(
            pattern=r"^[a-zA-Z0-9_\-\s]+\.(xlsx|xls)$",
            required_extensions=[".xlsx", ".xls"],
            max_file_size_mb=50,
            min_file_size_kb=1
        ),
        description="File name validation configuration"
    )
    
    # Sheet configurations
    sheets: Dict[str, SheetConfig] = Field(
        default_factory=dict,
        description="Sheet configurations by name pattern"
    )
    
    # Default sheet config
    default_sheet: SheetConfig = Field(
        default=SheetConfig(
            name=".*",
            is_required=False,
            is_processed=True,
            expected_headers=[
                "Клиент", "Продавец", "Счет", "Номер счета", "Дата счета",
                "УПД", "Отгружен", "Оплачен", "Выручка", "Маржа", "Стоимость",
                "Товар", "Поставщик", "Количество", "Цена закупки", "Цена продажи"
            ],
            required_headers=["Клиент", "Товар"],
            header_row_patterns=["Клиент", "Товар"],
            min_rows=1,
            min_columns=3
        ),
        description="Default configuration for sheets"
    )
    
    # НОВЫЕ ПОЛЯ: Бизнес-конфигурация
    business_rules: BusinessRulesConfig = Field(
        default_factory=BusinessRulesConfig,
        description="Конфигурация бизнес-правил"
    )
    
    # НОВЫЕ ПОЛЯ: Валидация периодов
    period_validation: PeriodValidationConfig = Field(
        default_factory=PeriodValidationConfig,
        description="Конфигурация валидации периодов"
    )
    
    # НОВЫЕ ПОЛЯ: Валидация путей
    file_path_validation: FilePathValidationConfig = Field(
        default_factory=FilePathValidationConfig,
        description="Конфигурация валидации путей"
    )
    
    # Validation rules
    strict_mode: bool = Field(
        default=False, 
        description="Strict validation mode"
    )
    allow_unknown_sheets: bool = Field(
        default=True, 
        description="Allow unknown sheets"
    )
    skip_empty_sheets: bool = Field(
        default=True, 
        description="Skip empty sheets"
    )
    
    # Error handling
    max_errors_per_sheet: int = Field(
        default=10, 
        description="Maximum errors per sheet"
    )
    max_warnings_per_sheet: int = Field(
        default=20, 
        description="Maximum warnings per sheet"
    )
    
    def get_sheet_config(self, sheet_name: str) -> SheetConfig:
        """Get configuration for specific sheet."""
        for pattern, config in self.sheets.items():
            if config.matches_name(sheet_name):
                return config
        
        # Return default config if no specific config found
        return self.default_sheet
    
    def is_sheet_allowed(self, sheet_name: str) -> bool:
        """Check if sheet is allowed for processing."""
        if self.allow_unknown_sheets:
            return True
        
        # Check if there's a specific config for this sheet
        for pattern, config in self.sheets.items():
            if config.matches_name(sheet_name):
                return config.is_processed
        
        return False
    
    def get_required_sheets(self) -> List[str]:
        """Get list of required sheet names."""
        required = []
        for pattern, config in self.sheets.items():
            if config.is_required:
                required.append(pattern)
        return required


# Default configurations
DEFAULT_EXCEL_CONFIG = ExcelValidationConfig(
    file_name=FileNameConfig(
        pattern=r"^[a-zA-Z0-9_\-\s]+\.(xlsx|xls)$",
        required_extensions=[".xlsx", ".xls"],
        max_file_size_mb=50,
        min_file_size_kb=1
    ),
    sheets={
        # Конфигурация для листов с данными сделок
        ".*": SheetConfig(
            name=".*",
            is_required=False,
            is_processed=True,
            expected_headers=[
                "Клиент", "Продавец", "Счет", "Номер счета", "Дата счета",
                "УПД", "Отгружен", "Оплачен", "Выручка", "Маржа", "Стоимость",
                "Товар", "Поставщик", "Количество", "Цена закупки", "Цена продажи"
            ],
            required_headers=["Клиент", "Товар"],
            optional_headers=[
                "Дата забора", "Откат", "Комментарий", "Примечание"
            ],
            header_row_patterns=["Клиент", "Товар"],
            min_rows=1,
            min_columns=3,
            allow_empty=False,
            allow_extra_headers=True,
            strict_header_match=False,
            business_rules=BusinessRulesConfig(
                require_client_data=True,
                require_invoice_data=True,
                require_financial_data=True,
                require_product_data=True,
                validate_financial_consistency=True,
                min_deals_per_sheet=1
            ),
            period_validation=PeriodValidationConfig(
                require_period_in_sheet_name=True,
                strict_period_validation=False,
                allow_future_periods=False
            )
        ),
        
        # Конфигурация для служебных листов (пропускаем)
        "^(Служебный|Service|Temp|Временный).*": SheetConfig(
            name="^(Служебный|Service|Temp|Временный).*",
            is_required=False,
            is_processed=False,
            expected_headers=[],
            required_headers=[],
            allow_empty=True,
            allow_extra_headers=True,
            business_rules=BusinessRulesConfig(
                require_client_data=False,
                require_invoice_data=False,
                require_financial_data=False,
                require_product_data=False,
                validate_financial_consistency=False
            ),
            period_validation=PeriodValidationConfig(
                require_period_in_sheet_name=False
            )
        ),
        
        # Конфигурация для листов с итогами (пропускаем)
        "^(Итоги|Summary|Сводка).*": SheetConfig(
            name="^(Итоги|Summary|Сводка).*",
            is_required=False,
            is_processed=False,
            expected_headers=[],
            required_headers=[],
            allow_empty=True,
            allow_extra_headers=True,
            business_rules=BusinessRulesConfig(
                require_client_data=False,
                require_invoice_data=False,
                require_financial_data=False,
                require_product_data=False,
                validate_financial_consistency=False
            ),
            period_validation=PeriodValidationConfig(
                require_period_in_sheet_name=False
            )
        )
    },
    business_rules=BusinessRulesConfig(
        require_client_data=True,
        require_invoice_data=True,
        require_financial_data=True,
        require_product_data=True,
        validate_financial_consistency=True,
        min_deals_per_sheet=1
    ),
    period_validation=PeriodValidationConfig(
        require_period_in_sheet_name=True,
        strict_period_validation=False,
        allow_future_periods=False
    ),
    file_path_validation=FilePathValidationConfig(
        require_valid_source_directory=True,
        validate_file_accessibility=True,
        validate_file_permissions=True,
        allow_network_paths=True
    ),
    strict_mode=False,
    allow_unknown_sheets=True,
    skip_empty_sheets=True,
    max_errors_per_sheet=10,
    max_warnings_per_sheet=20
)

# Конфигурация для строгого режима
STRICT_EXCEL_CONFIG = ExcelValidationConfig(
    file_name=FileNameConfig(
        pattern=r"^[a-zA-Z0-9_\-\s]+_\d{4}_\d{2}\.(xlsx|xls)$",
        required_extensions=[".xlsx"],
        max_file_size_mb=20,
        min_file_size_kb=1
    ),
    sheets={
        ".*": SheetConfig(
            name=".*",
            is_required=True,
            is_processed=True,
            expected_headers=[
                "Клиент", "Продавец", "Счет", "Номер счета", "Дата счета",
                "УПД", "Отгружен", "Оплачен", "Выручка", "Маржа", "Стоимость",
                "Товар", "Поставщик", "Количество", "Цена закупки", "Цена продажи"
            ],
            required_headers=[
                "Клиент", "Товар", "Количество", "Цена продажи"
            ],
            header_row_patterns=["Клиент"],
            min_rows=2,
            min_columns=5,
            allow_empty=False,
            allow_extra_headers=False,
            strict_header_match=True,
            business_rules=BusinessRulesConfig(
                require_client_data=True,
                require_invoice_data=True,
                require_financial_data=True,
                require_product_data=True,
                validate_financial_consistency=True,
                min_deals_per_sheet=2
            ),
            period_validation=PeriodValidationConfig(
                require_period_in_sheet_name=True,
                strict_period_validation=True,
                allow_future_periods=False
            )
        )
    },
    business_rules=BusinessRulesConfig(
        require_client_data=True,
        require_invoice_data=True,
        require_financial_data=True,
        require_product_data=True,
        validate_financial_consistency=True,
        min_deals_per_sheet=2
    ),
    period_validation=PeriodValidationConfig(
        require_period_in_sheet_name=True,
        strict_period_validation=True,
        allow_future_periods=False
    ),
    file_path_validation=FilePathValidationConfig(
        require_valid_source_directory=True,
        validate_file_accessibility=True,
        validate_file_permissions=True,
        allow_network_paths=False
    ),
    strict_mode=True,
    allow_unknown_sheets=False,
    skip_empty_sheets=True,
    max_errors_per_sheet=5,
    max_warnings_per_sheet=10
) 