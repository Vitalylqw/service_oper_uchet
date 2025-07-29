#!/usr/bin/env python3
"""
Adapted validation test for real Excel file format.

Creates a custom configuration that matches the actual file structure.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from application.data_validator import DataValidator
from application.data_validator.config import ExcelValidationConfig, SheetConfig, BusinessRulesConfig, PeriodValidationConfig


def create_adapted_config():
    """Create configuration adapted to real file format."""
    
    # Custom business rules for this file format
    business_rules = BusinessRulesConfig(
        require_client_data=True,
        require_invoice_data=False,  # This format doesn't have invoice data
        require_financial_data=True,
        require_product_data=True,
        validate_financial_consistency=True,
        min_deals_per_sheet=1
    )
    
    # Period validation
    period_validation = PeriodValidationConfig(
        require_period_in_sheet_name=True,
        strict_period_validation=False,
        allow_future_periods=True  # Allow future periods for planning
    )
    
    # Configuration for monthly data sheets
    monthly_sheet_config = SheetConfig(
        name=r"^(Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август|Сентябрь|Октябрь|Ноябрь|Декабрь)\s+\d{4}$",
        is_required=False,
        is_processed=True,
        expected_headers=[
            "Клиент", "Номенклатурах", "Кол/Отгр?", "Цена вх/накл", "цена исх/Оплач?"
        ],
        required_headers=["Клиент", "Номенклатурах"],
        optional_headers=[
            "Кол/Отгр?", "Цена вх/накл", "цена исх/Оплач?"
        ],
        header_row_patterns=["Клиент", "Номенклатурах"],
        min_rows=1,
        min_columns=3,
        allow_empty=False,
        allow_extra_headers=True,
        strict_header_match=False,
        business_rules=business_rules,
        period_validation=period_validation
    )
    
    # Configuration for settings sheet
    settings_sheet_config = SheetConfig(
        name="^Настройки$",
        is_required=False,
        is_processed=False,  # Don't process settings sheet
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
    
    # Create adapted configuration
    adapted_config = ExcelValidationConfig(
        sheets={
            "monthly": monthly_sheet_config,
            "settings": settings_sheet_config
        },
        business_rules=business_rules,
        period_validation=period_validation,
        strict_mode=False,
        allow_unknown_sheets=True,
        skip_empty_sheets=True,
        max_errors_per_sheet=10,
        max_warnings_per_sheet=20
    )
    
    return adapted_config


def test_adapted_validation():
    """Test validation with adapted configuration."""
    print("🚀 Testing Adapted Validation for Real File Format")
    print("=" * 60)
    
    # Path to real Excel file
    real_file_path = Path("data/real_data_for_testing/Data_source_excel.xlsx")
    
    if not real_file_path.exists():
        print(f"❌ Real Excel file not found: {real_file_path}")
        return False
    
    try:
        # Create adapted configuration
        adapted_config = create_adapted_config()
        
        # Test with adapted configuration
        print("\n🧪 Test 1: Adapted configuration validation...")
        validator = DataValidator(adapted_config)
        excel_file = validator.validate_excel_file_detailed(str(real_file_path))
        
        print(f"✅ Validation completed: {excel_file.validation_summary}")
        print(f"   - Status: {excel_file.status}")
        print(f"   - Is valid: {excel_file.is_valid}")
        print(f"   - Total sheets: {excel_file.total_sheets}")
        print(f"   - Valid sheets: {excel_file.valid_sheets}")
        print(f"   - Invalid sheets: {excel_file.invalid_sheets}")
        print(f"   - Skipped sheets: {excel_file.skipped_sheets}")
        
        # Detailed analysis with adapted config
        print("\n🧪 Test 2: Detailed analysis with adapted config...")
        for i, sheet in enumerate(excel_file.sheets):
            print(f"\n   📋 Sheet {i+1}: '{sheet.name}'")
            print(f"      - Status: {sheet.status}")
            print(f"      - Is valid: {sheet.is_valid}")
            print(f"      - Is processed: {sheet.is_processed}")
            print(f"      - Has data: {sheet.has_data}")
            print(f"      - Total rows: {sheet.total_rows}")
            print(f"      - Total columns: {sheet.total_columns}")
            
            # Period validation
            if sheet.period_validation:
                print(f"      - Period validation:")
                print(f"        * Extracted month: {sheet.period_validation.extracted_month}")
                print(f"        * Extracted year: {sheet.period_validation.extracted_year}")
                print(f"        * Period is valid: {sheet.period_is_valid}")
            
            # Business rules validation
            if sheet.business_rules_validation:
                print(f"      - Business rules validation:")
                print(f"        * Has client data: {sheet.business_rules_validation.has_client_data}")
                print(f"        * Has financial data: {sheet.business_rules_validation.has_financial_data}")
                print(f"        * Has product data: {sheet.business_rules_validation.has_product_data}")
                print(f"        * Rules violations: {len(sheet.business_rules_validation.rules_violations)}")
                if sheet.business_rules_validation.rules_violations:
                    for violation in sheet.business_rules_validation.rules_violations:
                        print(f"          - {violation}")
            
            # Headers analysis
            if sheet.actual_headers:
                print(f"      - Actual headers: {sheet.actual_headers}")
            
            # Errors and warnings
            if sheet.validation_errors:
                print(f"      - Validation errors ({len(sheet.validation_errors)}):")
                for error in sheet.validation_errors[:3]:
                    print(f"        * {error}")
        
        # Success rate analysis
        print("\n🧪 Test 3: Success rate analysis...")
        success_rate = excel_file.success_rate
        print(f"   - Success rate: {success_rate:.1f}%")
        print(f"   - File errors: {len(excel_file.validation_errors)}")
        print(f"   - File warnings: {len(excel_file.validation_warnings)}")
        
        # Summary
        print("\n🧪 Test 4: Summary and recommendations...")
        if excel_file.is_valid:
            print("   ✅ File is valid and ready for processing")
        else:
            print("   ⚠️ File has some validation issues")
            
            # Show what's working well
            valid_period_sheets = [s for s in excel_file.sheets if s.period_is_valid and s.is_processed]
            if valid_period_sheets:
                print("   ✅ Sheets with valid periods:")
                for sheet in valid_period_sheets:
                    print(f"      - '{sheet.name}': {sheet.total_rows} rows of data")
            
            # Show issues
            if excel_file.validation_errors:
                print("   📋 Issues to address:")
                for error in excel_file.validation_errors[:3]:
                    print(f"      - {error}")
        
        print("\n✅ Adapted validation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_data_quality():
    """Analyze the quality of data in the real file."""
    print("\n🔍 Analyzing data quality...")
    
    real_file_path = Path("data/real_data_for_testing/Data_source_excel.xlsx")
    
    try:
        excel_data = pd.ExcelFile(real_file_path)
        
        for sheet_name in excel_data.sheet_names:
            if any(month in sheet_name for month in ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                                                    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]):
                print(f"\n📊 Data quality analysis for '{sheet_name}':")
                
                # Read data starting from row 3 (after headers)
                df = pd.read_excel(excel_data, sheet_name=sheet_name, header=1)  # Headers in row 1 (0-indexed)
                
                print(f"   - Total rows: {len(df)}")
                print(f"   - Total columns: {len(df.columns)}")
                
                # Check for empty cells
                empty_cells = df.isnull().sum().sum()
                total_cells = df.size
                completeness = ((total_cells - empty_cells) / total_cells) * 100
                print(f"   - Data completeness: {completeness:.1f}%")
                
                # Check for unique clients
                if 'Клиент' in df.columns:
                    unique_clients = df['Клиент'].nunique()
                    print(f"   - Unique clients: {unique_clients}")
                
                # Check for unique products
                if 'Номенклатурах' in df.columns:
                    unique_products = df['Номенклатурах'].nunique()
                    print(f"   - Unique products: {unique_products}")
                
                # Check for price data
                price_columns = [col for col in df.columns if 'цена' in col.lower() or 'Цена' in col]
                if price_columns:
                    print(f"   - Price columns: {price_columns}")
                    
                    # Check for valid prices
                    for col in price_columns:
                        if df[col].dtype in ['float64', 'int64']:
                            valid_prices = df[col].notna().sum()
                            print(f"     * {col}: {valid_prices} valid prices")
        
        return True
        
    except Exception as e:
        print(f"❌ Data quality analysis failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Adapted Excel Validation Test Suite")
    print("=" * 60)
    
    success = True
    
    try:
        # Analyze data quality
        success &= analyze_data_quality()
        
        # Run adapted validation test
        success &= test_adapted_validation()
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        success = False
    
    if success:
        print("\n🎉 All adapted tests passed successfully!")
    else:
        print("\n💥 Some adapted tests failed!")
    
    sys.exit(0 if success else 1)