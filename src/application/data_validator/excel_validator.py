"""
Excel File Validator.

Comprehensive validator for Excel files with file name validation, sheet validation,
and data structure validation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

import pandas as pd
from loguru import logger

from domain.models import ExcelFile, ExcelSheet, FileValidationStatus, SheetValidationStatus
from .config import ExcelValidationConfig, DEFAULT_EXCEL_CONFIG
from .models import ErrorSeverity, ValidationError, ValidationResult


class ExcelFileValidator:
    """
    Comprehensive Excel file validator.
    
    Validates:
    - File name and extension
    - File size and integrity
    - Sheet structure and names
    - Header validation
    - Data structure validation
    - Period validation (NEW)
    - Business rules validation (NEW)
    - File path validation (NEW)
    """
    
    def __init__(self, config: Optional[ExcelValidationConfig] = None):
        """
        Initialize validator with configuration.
        
        Args:
            config: Validation configuration, uses default if not provided
        """
        self.config = config or DEFAULT_EXCEL_CONFIG
        logger.info("ExcelFileValidator initialized with configuration")
    
    def validate_file(self, file_path: str | Path, expected_source_directory: Optional[str] = None) -> ExcelFile:
        """
        Validate Excel file and return ExcelFile model.
        
        Args:
            file_path: Path to Excel file
            expected_source_directory: Expected source directory for file validation
            
        Returns:
            ExcelFile model with validation results
        """
        file_path = Path(file_path)
        logger.info(f"Starting comprehensive Excel validation for: {file_path}")
        
        # Create ExcelFile model
        excel_file = self._create_excel_file_model(file_path)
        
        try:
            # Validate file basics
            self._validate_file_basics(excel_file)
            
            # НОВАЯ ВАЛИДАЦИЯ: Проверка пути к файлу
            if self.config.file_path_validation.validate_file_accessibility:
                excel_file.validate_file_location(expected_source_directory)
            
            if excel_file.status == FileValidationStatus.INVALID:
                return excel_file
            
            # Load Excel file
            excel_data = self._load_excel_file(file_path)
            if not excel_data:
                excel_file.add_error("Не удалось загрузить Excel файл")
                return excel_file
            
            # Validate sheets
            self._validate_sheets(excel_file, excel_data)
            
            # НОВАЯ ВАЛИДАЦИЯ: Проверка периодов всех листов
            if self.config.period_validation.require_period_in_sheet_name:
                excel_file.validate_all_sheet_periods()
            
            # НОВАЯ ВАЛИДАЦИЯ: Проверка бизнес-правил всех листов
            excel_file.validate_all_business_rules(self.config.business_rules)
            
            # Update statistics
            excel_file.update_sheet_stats()
            
            # Final validation
            self._finalize_validation(excel_file)
            
            logger.info(f"Excel validation completed: {excel_file.validation_summary}")
            return excel_file
            
        except Exception as e:
            logger.error(f"Unexpected error during Excel validation: {e}")
            excel_file.add_error(f"Неожиданная ошибка валидации: {str(e)}")
            excel_file.status = FileValidationStatus.ERROR
            return excel_file
    
    def _create_excel_file_model(self, file_path: Path) -> ExcelFile:
        """Create ExcelFile model from file path."""
        # Calculate file hash
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # Get file modification time
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        return ExcelFile(
            file_path=str(file_path.absolute()),
            file_name=file_path.name,
            file_extension=file_path.suffix.lower(),
            file_size=file_path.stat().st_size,
            file_hash=file_hash,
            required_sheets=self.config.get_required_sheets(),
            allowed_sheets=list(self.config.sheets.keys()),
            name_pattern=self.config.file_name.pattern,
            last_modified=last_modified,
            file_source="local"  # Default source, can be updated later
        )
    
    def _validate_file_basics(self, excel_file: ExcelFile) -> None:
        """Validate basic file properties."""
        # Validate file name
        if not self.config.file_name.validate_name(excel_file.file_name):
            excel_file.add_error(
                f"Название файла не соответствует паттерну: {self.config.file_name.pattern}"
            )
            excel_file.name_is_valid = False
            excel_file.name_validation_error = "Название файла не соответствует требованиям"
        else:
            excel_file.name_is_valid = True
        
        # Validate extension
        if not self.config.file_name.validate_extension(excel_file.file_extension):
            excel_file.add_error(
                f"Неподдерживаемое расширение файла: {excel_file.file_extension}. "
                f"Поддерживаемые: {', '.join(self.config.file_name.required_extensions)}"
            )
        
        # Validate file size
        if not self.config.file_name.validate_size(excel_file.file_size):
            size_mb = excel_file.file_size / (1024 * 1024)
            excel_file.add_error(
                f"Размер файла {size_mb:.2f} МБ не соответствует требованиям "
                f"({self.config.file_name.min_file_size_kb} КБ - {self.config.file_name.max_file_size_mb} МБ)"
            )
    
    def _load_excel_file(self, file_path: Path) -> Optional[pd.ExcelFile]:
        """Load Excel file for validation."""
        try:
            return pd.ExcelFile(file_path)
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            return None
    
    def _validate_sheets(self, excel_file: ExcelFile, excel_data: pd.ExcelFile) -> None:
        """Validate all sheets in Excel file."""
        excel_file.total_sheets = len(excel_data.sheet_names)
        
        for sheet_index, sheet_name in enumerate(excel_data.sheet_names):
            logger.info(f"Validating sheet: {sheet_name}")
            
            # Create sheet model
            sheet = ExcelSheet(
                id=excel_file.id,  # Use file ID as parent
                name=sheet_name,
                index=sheet_index
            )
            
            # Get sheet configuration
            sheet_config = self.config.get_sheet_config(sheet_name)
            sheet.is_required = sheet_config.is_required
            sheet.is_processed = sheet_config.is_processed
            sheet.expected_headers = sheet_config.expected_headers
            
            # Check if sheet should be processed
            if not self.config.is_sheet_allowed(sheet_name):
                sheet.mark_skipped()
                excel_file.sheets.append(sheet)
                continue
            
            # Validate sheet structure
            self._validate_sheet_structure(sheet, sheet_config, excel_data)
            
            # НОВАЯ ВАЛИДАЦИЯ: Проверка периода листа
            if sheet_config.period_validation.require_period_in_sheet_name:
                sheet.validate_sheet_period()
            
            # НОВАЯ ВАЛИДАЦИЯ: Проверка бизнес-правил листа
            sheet.validate_business_rules(sheet_config.business_rules)
            
            # Add sheet to file
            excel_file.sheets.append(sheet)
    
    def _validate_sheet_structure(
        self, 
        sheet: ExcelSheet, 
        sheet_config: Any, 
        excel_data: pd.ExcelFile
    ) -> None:
        """Validate individual sheet structure."""
        try:
            # Read sheet data
            df = pd.read_excel(excel_data, sheet_name=sheet.name, header=None)
            sheet.total_rows = len(df)
            sheet.total_columns = len(df.columns) if not df.empty else 0
            
            # Check if sheet is empty
            if df.empty:
                if sheet_config.allow_empty:
                    sheet.mark_skipped()
                    sheet.add_warning("Лист пустой")
                else:
                    sheet.add_error("Лист пустой, но должен содержать данные")
                return
            
            # Find header row
            header_row = self._find_header_row(df, sheet_config)
            if header_row is None:
                sheet.add_error("Не удалось найти строку с заголовками")
                return
            
            sheet.header_row = header_row
            sheet.data_start_row = header_row + sheet_config.data_start_offset
            
            # Extract and validate headers
            self._validate_headers(sheet, df, sheet_config, header_row)
            
            # Validate data structure
            self._validate_data_structure(sheet, df, sheet_config)
            
            # Mark as valid if no errors
            if not sheet.has_errors:
                sheet.mark_valid()
                sheet.has_data = True
                sheet.is_empty = False
            
        except Exception as e:
            logger.error(f"Error validating sheet '{sheet.name}': {e}")
            sheet.add_error(f"Ошибка валидации листа: {str(e)}")
    
    def _find_header_row(self, df: pd.DataFrame, sheet_config: Any) -> Optional[int]:
        """Find header row in sheet."""
        patterns = sheet_config.header_row_patterns
        max_search = sheet_config.max_header_search_rows
        
        for row_idx in range(min(max_search, len(df))):
            row_values = [str(val).strip() for val in df.iloc[row_idx] if pd.notna(val)]
            
            # Check if any pattern matches
            for pattern in patterns:
                if any(pattern.lower() in val.lower() for val in row_values):
                    return row_idx
        
        return None
    
    def _validate_headers(
        self, 
        sheet: ExcelSheet, 
        df: pd.DataFrame, 
        sheet_config: Any, 
        header_row: int
    ) -> None:
        """Validate headers in sheet."""
        try:
            # Extract headers
            headers = [str(col).strip() for col in df.iloc[header_row] if pd.notna(col)]
            sheet.actual_headers = headers
            
            # Check required headers
            missing_required = sheet_config.get_missing_required_headers(headers)
            if missing_required:
                sheet.add_error(
                    f"Отсутствуют обязательные заголовки: {', '.join(missing_required)}"
                )
                sheet.missing_headers = missing_required
            
            # Check extra headers
            if not sheet_config.allow_extra_headers:
                extra_headers = sheet_config.get_extra_headers(headers)
                if extra_headers:
                    sheet.add_warning(
                        f"Обнаружены лишние заголовки: {', '.join(extra_headers)}"
                    )
                    sheet.extra_headers = extra_headers
            
            # Validate header count
            if len(headers) < sheet_config.min_columns:
                sheet.add_error(
                    f"Недостаточно колонок: {len(headers)}, минимум {sheet_config.min_columns}"
                )
            
            if sheet_config.max_columns and len(headers) > sheet_config.max_columns:
                sheet.add_warning(
                    f"Слишком много колонок: {len(headers)}, максимум {sheet_config.max_columns}"
                )
                
        except Exception as e:
            sheet.add_error(f"Ошибка валидации заголовков: {str(e)}")
    
    def _validate_data_structure(
        self, 
        sheet: ExcelSheet, 
        df: pd.DataFrame, 
        sheet_config: Any
    ) -> None:
        """Validate data structure in sheet."""
        try:
            if sheet.data_start_row is None:
                return
            
            # Calculate data rows
            data_rows = len(df) - sheet.data_start_row
            
            if data_rows < sheet_config.min_rows:
                sheet.add_error(
                    f"Недостаточно строк данных: {data_rows}, минимум {sheet_config.min_rows}"
                )
            
            if sheet_config.max_rows and data_rows > sheet_config.max_rows:
                sheet.add_warning(
                    f"Слишком много строк данных: {data_rows}, максимум {sheet_config.max_rows}"
                )
            
            # Check for empty data
            if data_rows <= 0:
                sheet.add_warning("Нет строк с данными после заголовков")
            
        except Exception as e:
            sheet.add_error(f"Ошибка валидации структуры данных: {str(e)}")
    
    def _finalize_validation(self, excel_file: ExcelFile) -> None:
        """Finalize file validation."""
        # Check for missing required sheets
        missing_required = excel_file.get_missing_required_sheets()
        if missing_required:
            excel_file.add_error(
                f"Отсутствуют обязательные листы: {', '.join(missing_required)}"
            )
        
        # Check if file has any valid sheets
        valid_sheets = excel_file.get_valid_sheets()
        if not valid_sheets and excel_file.total_sheets > 0:
            excel_file.add_error("Нет валидных листов для обработки")
        
        # НОВАЯ ПРОВЕРКА: Проверка бизнес-правил на уровне файла
        if self.config.business_rules.min_deals_per_sheet:
            sheets_with_insufficient_deals = []
            for sheet in excel_file.sheets:
                if sheet.is_processed and sheet.has_data:
                    # This would need to be implemented with actual deal counting
                    # For now, we'll just check if sheet has data
                    pass
            
            if sheets_with_insufficient_deals:
                excel_file.add_warning(
                    f"Листы с недостаточным количеством сделок: {[s.name for s in sheets_with_insufficient_deals]}"
                )
        
        # Mark file as valid if no critical errors
        if not excel_file.validation_errors:
            excel_file.mark_valid()
        
        # Add warnings for skipped sheets
        skipped_count = len([s for s in excel_file.sheets if s.status == SheetValidationStatus.SKIPPED])
        if skipped_count > 0:
            excel_file.add_warning(f"Пропущено листов: {skipped_count}")
    
    def get_validation_result(self, excel_file: ExcelFile) -> ValidationResult:
        """
        Convert ExcelFile model to ValidationResult.
        
        Args:
            excel_file: Validated ExcelFile model
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(
            is_valid=excel_file.is_valid,
            file_path=excel_file.file_path
        )
        
        # Add file-level errors
        for error in excel_file.validation_errors:
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.ERROR,
                    code="FILE_VALIDATION_ERROR",
                    message=error
                )
            )
        
        # Add file-level warnings
        for warning in excel_file.validation_warnings:
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.WARNING,
                    code="FILE_VALIDATION_WARNING",
                    message=warning
                )
            )
        
        # Add sheet-level errors and warnings
        for sheet in excel_file.sheets:
            for error in sheet.validation_errors:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.ERROR,
                        code="SHEET_VALIDATION_ERROR",
                        message=error,
                        sheet_name=sheet.name
                    )
                )
            
            for warning in sheet.validation_warnings:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.WARNING,
                        code="SHEET_VALIDATION_WARNING",
                        message=warning,
                        sheet_name=sheet.name
                    )
                )
        
        return result 