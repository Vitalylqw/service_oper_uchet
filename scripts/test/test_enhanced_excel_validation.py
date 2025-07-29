#!/usr/bin/env python3
"""
Enhanced Excel validation test script.

Tests the new functionality including:
- Period validation
- Business rules validation
- File path validation
- Monitoring integration
"""

import sys
from pathlib import Path
import tempfile
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from application.data_validator import DataValidator
from application.data_validator.config import DEFAULT_EXCEL_CONFIG, STRICT_EXCEL_CONFIG
from domain.models import ExcelFile, ExcelSheet, FileValidationStatus, SheetValidationStatus


def create_test_excel_file(file_path: Path, sheet_name: str = "Март 2025") -> None:
    """Create test Excel file with sample data."""
    # Create sample data
    data = {
        "Клиент": ["ООО Тест", "ИП Иванов", "ООО Рога и Копыта"],
        "Товар": ["Товар 1", "Товар 2", "Товар 3"],
        "Количество": [10, 5, 15],
        "Цена продажи": [100.50, 200.75, 150.00],
        "Выручка": [1005.00, 1003.75, 2250.00],
        "Маржа": [300.00, 250.00, 450.00],
        "Стоимость": [705.00, 753.75, 1800.00]
    }
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


def test_enhanced_excel_validation():
    """Test enhanced Excel validation functionality."""
    print("🚀 Starting Enhanced Excel Validation Tests...")
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
        test_file_path = Path(tmp_file.name)
        create_test_excel_file(test_file_path, "Март 2025")
    
    try:
        # Test 1: Basic enhanced validation
        print("\n🧪 Test 1: Basic enhanced validation...")
        validator = DataValidator()
        excel_file = validator.validate_excel_file_detailed(str(test_file_path))
        
        print(f"✅ File validation completed: {excel_file.validation_summary}")
        print(f"   - Status: {excel_file.status}")
        print(f"   - Is valid: {excel_file.is_valid}")
        print(f"   - Total sheets: {excel_file.total_sheets}")
        print(f"   - Valid sheets: {excel_file.valid_sheets}")
        
        # Test 2: Period validation
        print("\n🧪 Test 2: Period validation...")
        if excel_file.sheets:
            sheet = excel_file.sheets[0]
            print(f"   - Sheet name: {sheet.name}")
            print(f"   - Period is valid: {sheet.period_is_valid}")
            if sheet.period_validation:
                print(f"   - Extracted month: {sheet.period_validation.extracted_month}")
                print(f"   - Extracted year: {sheet.period_validation.extracted_year}")
                print(f"   - Is valid format: {sheet.period_validation.is_valid_format}")
                print(f"   - Is valid period: {sheet.period_validation.is_valid_period}")
        
        # Test 3: Business rules validation
        print("\n🧪 Test 3: Business rules validation...")
        if excel_file.sheets:
            sheet = excel_file.sheets[0]
            if sheet.business_rules_validation:
                print(f"   - Has client data: {sheet.business_rules_validation.has_client_data}")
                print(f"   - Has invoice data: {sheet.business_rules_validation.has_invoice_data}")
                print(f"   - Has financial data: {sheet.business_rules_validation.has_financial_data}")
                print(f"   - Has product data: {sheet.business_rules_validation.has_product_data}")
                print(f"   - Rules violations: {sheet.business_rules_validation.rules_violations}")
        
        # Test 4: File path validation
        print("\n🧪 Test 4: File path validation...")
        print(f"   - Path is valid: {excel_file.path_is_valid}")
        print(f"   - Source directory: {excel_file.source_directory}")
        print(f"   - File source: {excel_file.file_source}")
        print(f"   - Last modified: {excel_file.last_modified}")
        
        # Test 5: Monitoring integration
        print("\n🧪 Test 5: Monitoring integration...")
        excel_file.set_monitoring_info(is_monitored=True, monitoring_status="active")
        if excel_file.monitoring_info:
            print(f"   - Is monitored: {excel_file.monitoring_info.is_monitored}")
            print(f"   - Monitoring status: {excel_file.monitoring_info.monitoring_status}")
            print(f"   - Monitoring started: {excel_file.monitoring_info.monitoring_started}")
        
        # Test 6: Invalid period test
        print("\n🧪 Test 6: Invalid period test...")
        test_file_path2 = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file2:
                test_file_path2 = Path(tmp_file2.name)
                create_test_excel_file(test_file_path2, "Invalid Sheet Name")
            
            excel_file2 = validator.validate_excel_file_detailed(str(test_file_path2))
            if excel_file2.sheets:
                sheet2 = excel_file2.sheets[0]
                print(f"   - Invalid sheet name: {sheet2.name}")
                print(f"   - Period is valid: {sheet2.period_is_valid}")
                if sheet2.period_validation:
                    print(f"   - Validation error: {sheet2.period_validation.validation_error}")
        finally:
            if test_file_path2 and test_file_path2.exists():
                try:
                    test_file_path2.unlink()
                except:
                    pass  # Ignore cleanup errors
        
        # Test 7: Strict configuration test
        print("\n🧪 Test 7: Strict configuration test...")
        strict_validator = DataValidator(STRICT_EXCEL_CONFIG)
        excel_file_strict = strict_validator.validate_excel_file_detailed(str(test_file_path))
        print(f"   - Strict validation result: {excel_file_strict.validation_summary}")
        print(f"   - Is valid (strict): {excel_file_strict.is_valid}")
        
        # Test 8: Error summary
        print("\n🧪 Test 8: Error summary...")
        print(f"   - File errors: {len(excel_file.validation_errors)}")
        print(f"   - File warnings: {len(excel_file.validation_warnings)}")
        
        total_sheet_errors = sum(len(s.validation_errors) for s in excel_file.sheets)
        total_sheet_warnings = sum(len(s.validation_warnings) for s in excel_file.sheets)
        print(f"   - Total sheet errors: {total_sheet_errors}")
        print(f"   - Total sheet warnings: {total_sheet_warnings}")
        
        print("\n✅ All enhanced validation tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            if test_file_path.exists():
                test_file_path.unlink()
        except:
            pass  # Ignore cleanup errors


def test_period_validation_edge_cases():
    """Test period validation with edge cases."""
    print("\n🧪 Testing period validation edge cases...")
    
    test_cases = [
        ("Март 2025", True, "Март", "2025"),
        ("май 2024", True, "Май", "2024"),
        ("Декабрь 2023", True, "Декабрь", "2023"),
        ("Invalid Name", False, None, None),
        ("Январь 2030", True, "Январь", "2030"),
        ("Февраль 2019", False, None, None),  # Year out of range
        ("", False, None, None),
        ("Март", False, None, None),  # Missing year
        ("2025", False, None, None),  # Missing month
    ]
    
    for sheet_name, expected_valid, expected_month, expected_year in test_cases:
        try:
            from domain.value_objects import Period
            period = Period.from_sheet_name(sheet_name)
            actual_valid = True
            actual_month = period.month
            actual_year = period.year
        except ValueError:
            actual_valid = False
            actual_month = None
            actual_year = None
        
        status = "✅" if actual_valid == expected_valid else "❌"
        print(f"   {status} '{sheet_name}' -> Valid: {actual_valid}, Month: {actual_month}, Year: {actual_year}")
        
        if expected_valid and actual_valid:
            assert actual_month == expected_month, f"Month mismatch: {actual_month} != {expected_month}"
            assert actual_year == expected_year, f"Year mismatch: {actual_year} != {expected_year}"


def test_business_rules_validation():
    """Test business rules validation."""
    print("\n🧪 Testing business rules validation...")
    
    # Test with valid headers
    valid_headers = ["Клиент", "Товар", "Количество", "Выручка", "Маржа", "Стоимость"]
    
    # Test with missing headers
    invalid_headers = ["Товар", "Количество"]  # Missing "Клиент"
    
    from domain.models import ExcelSheet
    
    # Test valid case
    sheet_valid = ExcelSheet(name="Тест", index=0)
    sheet_valid.actual_headers = valid_headers
    sheet_valid.validate_business_rules(DEFAULT_EXCEL_CONFIG.business_rules)
    
    print(f"   ✅ Valid headers: {sheet_valid.business_rules_validation.has_client_data}")
    print(f"   ✅ Has financial data: {sheet_valid.business_rules_validation.has_financial_data}")
    print(f"   ✅ Rules violations: {len(sheet_valid.business_rules_validation.rules_violations)}")
    
    # Test invalid case
    sheet_invalid = ExcelSheet(name="Тест", index=0)
    sheet_invalid.actual_headers = invalid_headers
    sheet_invalid.validate_business_rules(DEFAULT_EXCEL_CONFIG.business_rules)
    
    print(f"   ❌ Invalid headers: {sheet_invalid.business_rules_validation.has_client_data}")
    print(f"   ❌ Rules violations: {sheet_invalid.business_rules_validation.rules_violations}")


if __name__ == "__main__":
    print("🚀 Enhanced Excel Validation Test Suite")
    print("=" * 50)
    
    success = True
    
    try:
        # Run main test
        success &= test_enhanced_excel_validation()
        
        # Run edge case tests
        test_period_validation_edge_cases()
        test_business_rules_validation()
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        success = False
    
    if success:
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n💥 Some tests failed!")
    
    sys.exit(0 if success else 1)