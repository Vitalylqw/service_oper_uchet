"""
Configuration for Excel file validation.

Contains settings for file name validation, sheet validation, and data structure validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Pattern
import re

from pydantic import BaseModel, Field


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
    
    @property
    def name_pattern(self) -> Pattern[str]:
        """Get compiled name pattern."""
        return re.compile(self.name, re.IGNORECASE)
    
    def matches_name(self, sheet_name: str) -> bool:
        """Check if sheet name matches pattern."""
        return bool(self.name_pattern.match(sheet_name))
    
    def get_missing_required_headers(self, actual_headers: List[str]) -> List[str]:
        """Get missing required headers."""
        actual_lower = [h.lower().strip() for h in actual_headers]
        return [
            required for required in self.required_headers
            if not any(required.lower() in actual for actual in actual_lower)
        ]
    
    def get_extra_headers(self, actual_headers: List[str]) -> List[str]:
        """Get extra headers not in expected list."""
        if self.allow_extra_headers:
            return []
        
        expected_all = self.expected_headers + self.optional_headers
        expected_lower = [h.lower().strip() for h in expected_all]
        return [
            actual for actual in actual_headers
            if not any(actual.lower() in expected for expected in expected_lower)
        ]


class FileNameConfig(BaseModel):
    """Configuration for file name validation."""
    
    pattern: str = Field(..., description="Regex pattern for file name validation")
    required_extensions: List[str] = Field(
        default=[".xlsx", ".xls"], 
        description="Required file extensions"
    )
    max_file_size_mb: int = Field(
        default=50, 
        description="Maximum file size in MB"
    )
    min_file_size_kb: int = Field(
        default=1, 
        description="Minimum file size in KB"
    )
    
    # Name validation rules
    case_sensitive: bool = Field(default=False, description="Case sensitive matching")
    allow_spaces: bool = Field(default=True, description="Allow spaces in names")
    allow_special_chars: bool = Field(default=False, description="Allow special characters")
    
    @property
    def compiled_pattern(self) -> Pattern[str]:
        """Get compiled regex pattern."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        return re.compile(self.pattern, flags)
    
    def validate_name(self, file_name: str) -> bool:
        """Validate file name against pattern."""
        return bool(self.compiled_pattern.match(file_name))
    
    def validate_extension(self, extension: str) -> bool:
        """Validate file extension."""
        return extension.lower() in [ext.lower() for ext in self.required_extensions]
    
    def validate_size(self, size_bytes: int) -> bool:
        """Validate file size."""
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        return (
            size_kb >= self.min_file_size_kb and 
            size_mb <= self.max_file_size_mb
        )


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
            strict_header_match=False
        ),
        
        # Конфигурация для служебных листов (пропускаем)
        "^(Служебный|Service|Temp|Временный).*": SheetConfig(
            name="^(Служебный|Service|Temp|Временный).*",
            is_required=False,
            is_processed=False,
            expected_headers=[],
            required_headers=[],
            allow_empty=True,
            allow_extra_headers=True
        ),
        
        # Конфигурация для листов с итогами (пропускаем)
        "^(Итоги|Summary|Сводка).*": SheetConfig(
            name="^(Итоги|Summary|Сводка).*",
            is_required=False,
            is_processed=False,
            expected_headers=[],
            required_headers=[],
            allow_empty=True,
            allow_extra_headers=True
        )
    },
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
            strict_header_match=True
        )
    },
    strict_mode=True,
    allow_unknown_sheets=False,
    skip_empty_sheets=True,
    max_errors_per_sheet=5,
    max_warnings_per_sheet=10
) 