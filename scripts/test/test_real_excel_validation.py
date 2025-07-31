#!/usr/bin/env python3
"""
Real Excel file validation test.

Tests the enhanced validation functionality on real Excel file with data.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from application.data_validator import DataValidator
from application.data_validator.config import DEFAULT_EXCEL_CONFIG, STRICT_EXCEL_CONFIG
from domain.models import ExcelFile, ExcelSheet, FileValidationStatus, SheetValidationStatus


def test_real_excel_file():
    """Test enhanced validation on real Excel file."""
    print("🚀 Testing Enhanced Excel Validation on Real Data File")
    print("=" * 60)
    
    # Path to real Excel file
    real_file_path = Path("data/real_data_for_testing/Data_source_excel.xlsx")
    
    if not real_file_path.exists():
        print(f"❌ Real Excel file not found: {real_file_path}")
        return False
    
    print(f"📁 Testing file: {real_file_path}")
    print(f"📊 File size: {real_file_path.stat().st_size / 1024:.2f} KB")
    
    try:
        # Test 1: Basic validation with default config
        print("\n🧪 Test 1: Basic validation with default config...")
        validator = DataValidator()
        excel_file = validator.validate_excel_file_detailed(str(real_file_path))
        
        print(f"✅ Validation completed: {excel_file.validation_summary}")
        print(f"   - Status: {excel_file.status}")
        print(f"   - Is valid: {excel_file.is_valid}")
        print(f"   - Total sheets: {excel_file.total_sheets}")
        print(f"   - Valid sheets: {excel_file.valid_sheets}")
        print(f"   - Invalid sheets: {excel_file.invalid_sheets}")
        print(f"   - Skipped sheets: {excel_file.skipped_sheets}")
        
        # Test 2: Detailed sheet analysis
        print("\n🧪 Test 2: Detailed sheet analysis...")
        for i, sheet in enumerate(excel_file.sheets):
            print(f"\n   📋 Sheet {i+1}: '{sheet.name}'")
            print(f"      - Index: {sheet.index}")
            print(f"      - Status: {sheet.status}")
            print(f"      - Is valid: {sheet.is_valid}")
            print(f"      - Is required: {sheet.is_required}")
            print(f"      - Is processed: {sheet.is_processed}")
            print(f"      - Has data: {sheet.has_data}")
            print(f"      - Total rows: {sheet.total_rows}")
            print(f"      - Total columns: {sheet.total_columns}")
            print(f"      - Header row: {sheet.header_row}")
            print(f"      - Data start row: {sheet.data_start_row}")
            
            # Period validation
            if sheet.period_validation:
                print(f"      - Period validation:")
                print(f"        * Extracted month: {sheet.period_validation.extracted_month}")
                print(f"        * Extracted year: {sheet.period_validation.extracted_year}")
                print(f"        * Is valid format: {sheet.period_validation.is_valid_format}")
                print(f"        * Is valid period: {sheet.period_validation.is_valid_period}")
                print(f"        * Period is valid: {sheet.period_is_valid}")
            
            # Business rules validation
            if sheet.business_rules_validation:
                print(f"      - Business rules validation:")
                print(f"        * Has client data: {sheet.business_rules_validation.has_client_data}")
                print(f"        * Has invoice data: {sheet.business_rules_validation.has_invoice_data}")
                print(f"        * Has financial data: {sheet.business_rules_validation.has_financial_data}")
                print(f"        * Has product data: {sheet.business_rules_validation.has_product_data}")
                print(f"        * Rules violations: {len(sheet.business_rules_validation.rules_violations)}")
                if sheet.business_rules_validation.rules_violations:
                    for violation in sheet.business_rules_validation.rules_violations:
                        print(f"          - {violation}")
            
            # Headers analysis
            print(f"      - Headers analysis:")
            print(f"        * Expected headers: {len(sheet.expected_headers)}")
            print(f"        * Actual headers: {len(sheet.actual_headers)}")
            print(f"        * Missing headers: {len(sheet.missing_headers)}")
            print(f"        * Extra headers: {len(sheet.extra_headers)}")
            
            if sheet.actual_headers:
                print(f"        * Actual headers: {sheet.actual_headers[:5]}...")  # Show first 5
            
            # Errors and warnings
            if sheet.validation_errors:
                print(f"      - Validation errors ({len(sheet.validation_errors)}):")
                for error in sheet.validation_errors[:3]:  # Show first 3
                    print(f"        * {error}")
            
            if sheet.validation_warnings:
                print(f"      - Validation warnings ({len(sheet.validation_warnings)}):")
                for warning in sheet.validation_warnings[:3]:  # Show first 3
                    print(f"        * {warning}")
        
        # Test 3: File path validation
        print("\n🧪 Test 3: File path validation...")
        print(f"   - Path is valid: {excel_file.path_is_valid}")
        print(f"   - Source directory: {excel_file.source_directory}")
        print(f"   - File source: {excel_file.file_source}")
        print(f"   - Last modified: {excel_file.last_modified}")
        print(f"   - Change detected: {excel_file.change_detected}")
        
        # Test 4: Monitoring integration
        print("\n🧪 Test 4: Monitoring integration...")
        excel_file.set_monitoring_info(is_monitored=True, monitoring_status="active")
        if excel_file.monitoring_info:
            print(f"   - Is monitored: {excel_file.monitoring_info.is_monitored}")
            print(f"   - Monitoring status: {excel_file.monitoring_info.monitoring_status}")
            print(f"   - Monitoring started: {excel_file.monitoring_info.monitoring_started}")
            print(f"   - Change count: {excel_file.monitoring_info.change_count}")
        
        # Test 5: Strict configuration test
        print("\n🧪 Test 5: Strict configuration test...")
        strict_validator = DataValidator(STRICT_EXCEL_CONFIG)
        excel_file_strict = strict_validator.validate_excel_file_detailed(str(real_file_path))
        print(f"   - Strict validation result: {excel_file_strict.validation_summary}")
        print(f"   - Is valid (strict): {excel_file_strict.is_valid}")
        
        # Test 6: Success rate analysis
        print("\n🧪 Test 6: Success rate analysis...")
        success_rate = excel_file.success_rate
        print(f"   - Success rate: {success_rate:.1f}%")
        print(f"   - File errors: {len(excel_file.validation_errors)}")
        print(f"   - File warnings: {len(excel_file.validation_warnings)}")
        
        total_sheet_errors = sum(len(s.validation_errors) for s in excel_file.sheets)
        total_sheet_warnings = sum(len(s.validation_warnings) for s in excel_file.sheets)
        print(f"   - Total sheet errors: {total_sheet_errors}")
        print(f"   - Total sheet warnings: {total_sheet_warnings}")
        
        # Test 7: Financial validation (if applicable)
        print("\n🧪 Test 7: Financial validation...")
        for sheet in excel_file.sheets:
            if sheet.financial_validation:
                print(f"   📊 Sheet '{sheet.name}' financial data:")
                print(f"      - Revenue sum: {sheet.financial_validation.revenue_sum}")
                print(f"      - Margin sum: {sheet.financial_validation.margin_sum}")
                print(f"      - Cost sum: {sheet.financial_validation.cost_sum}")
                print(f"      - Financial consistency: {sheet.financial_validation.financial_consistency}")
                if sheet.financial_validation.financial_errors:
                    print(f"      - Financial errors: {sheet.financial_validation.financial_errors}")
        
        # Test 8: Summary and recommendations
        print("\n🧪 Test 8: Summary and recommendations...")
        if excel_file.is_valid:
            print("   ✅ File is valid and ready for processing")
        else:
            print("   ❌ File has validation issues that need attention")
            
            # Show main issues
            if excel_file.validation_errors:
                print("   📋 Main file issues:")
                for error in excel_file.validation_errors[:5]:
                    print(f"      - {error}")
            
            # Show sheet issues
            invalid_sheets = [s for s in excel_file.sheets if not s.is_valid and s.is_processed]
            if invalid_sheets:
                print("   📋 Sheets with issues:")
                for sheet in invalid_sheets:
                    print(f"      - '{sheet.name}': {len(sheet.validation_errors)} errors")
        
        print("\n✅ Real Excel file validation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_excel_structure():
    """Analyze the structure of the real Excel file."""
    print("\n🔍 Analyzing Excel file structure...")
    
    real_file_path = Path("data/real_data_for_testing/Data_source_excel.xlsx")
    
    try:
        # Read Excel file to analyze structure
        excel_data = pd.ExcelFile(real_file_path)
        
        print(f"📊 Excel file analysis:")
        print(f"   - Total sheets: {len(excel_data.sheet_names)}")
        print(f"   - Sheet names: {excel_data.sheet_names}")
        
        for sheet_name in excel_data.sheet_names:
            print(f"\n   📋 Sheet: '{sheet_name}'")
            df = pd.read_excel(excel_data, sheet_name=sheet_name, nrows=5)  # Read first 5 rows
            
            print(f"      - Shape: {df.shape}")
            print(f"      - Columns: {list(df.columns)}")
            print(f"      - Data types: {df.dtypes.tolist()}")
            
            # Check for period in sheet name
            if any(month in sheet_name for month in ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                                                    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]):
                print(f"      - ✅ Contains period information")
            else:
                print(f"      - ❌ No period information detected")
            
            # Check for business data
            business_columns = ["Клиент", "Товар", "Выручка", "Маржа", "Стоимость", "Счет", "Номер счета"]
            found_columns = [col for col in df.columns if any(bc in str(col) for bc in business_columns)]
            if found_columns:
                print(f"      - ✅ Contains business data: {found_columns}")
            else:
                print(f"      - ❌ No business data detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Real Excel File Validation Test Suite")
    print("=" * 60)
    
    success = True
    
    try:
        # Analyze file structure first
        success &= analyze_excel_structure()
        
        # Run main validation test
        success &= test_real_excel_file()
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        success = False
    
    if success:
        print("\n🎉 All real file tests passed successfully!")
    else:
        print("\n💥 Some real file tests failed!")
    
    sys.exit(0 if success else 1)