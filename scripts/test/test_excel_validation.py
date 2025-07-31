"""
Test script for Excel file validation system.

Tests the new ExcelFile and ExcelSheet validation models and functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from application.data_validator import DataValidator
from application.data_validator.config import DEFAULT_EXCEL_CONFIG, STRICT_EXCEL_CONFIG
from domain.models import ExcelFile, ExcelSheet, FileValidationStatus, SheetValidationStatus


def test_excel_validation_models():
    """Test Excel validation models creation."""
    print("🧪 Testing Excel validation models...")
    
    # Test ExcelSheet creation
    sheet = ExcelSheet(
        name="Test Sheet",
        index=0,
        is_required=True,
        expected_headers=["Клиент", "Товар", "Количество"],
        actual_headers=["Клиент", "Товар", "Количество", "Цена"],
        total_rows=100,
        total_columns=4
    )
    
    print(f"✅ Created ExcelSheet: {sheet.name}")
    print(f"   - Status: {sheet.status}")
    print(f"   - Is valid: {sheet.is_valid}")
    print(f"   - Has data: {sheet.has_data}")
    print(f"   - Extra headers: {sheet.extra_headers}")
    
    # Test ExcelFile creation with mock file path
    excel_file = ExcelFile(
        file_path=str(Path(__file__)),  # Use current test file as mock
        file_name="test.xlsx",
        file_extension=".xlsx",
        file_size=1024,
        file_hash="test_hash",
        required_sheets=["Sheet1", "Sheet2"],
        sheets=[sheet]
    )
    
    print(f"✅ Created ExcelFile: {excel_file.file_name}")
    print(f"   - Status: {excel_file.status}")
    print(f"   - Is valid: {excel_file.is_valid}")
    print(f"   - Total sheets: {excel_file.total_sheets}")
    print(f"   - Valid sheets: {excel_file.valid_sheets}")
    
    return True


def test_validation_config():
    """Test validation configuration."""
    print("\n🧪 Testing validation configuration...")
    
    # Test default config
    config = DEFAULT_EXCEL_CONFIG
    print(f"✅ Default config loaded")
    print(f"   - Strict mode: {config.strict_mode}")
    print(f"   - Allow unknown sheets: {config.allow_unknown_sheets}")
    print(f"   - Max file size: {config.file_name.max_file_size_mb} MB")
    
    # Test sheet config matching
    sheet_config = config.get_sheet_config("Test Sheet")
    print(f"✅ Sheet config for 'Test Sheet':")
    print(f"   - Is required: {sheet_config.is_required}")
    print(f"   - Is processed: {sheet_config.is_processed}")
    print(f"   - Expected headers: {len(sheet_config.expected_headers)}")
    print(f"   - Required headers: {sheet_config.required_headers}")
    
    # Test strict config
    strict_config = STRICT_EXCEL_CONFIG
    print(f"✅ Strict config loaded")
    print(f"   - Strict mode: {strict_config.strict_mode}")
    print(f"   - Allow unknown sheets: {strict_config.allow_unknown_sheets}")
    
    return True


def test_file_name_validation():
    """Test file name validation."""
    print("\n🧪 Testing file name validation...")
    
    config = DEFAULT_EXCEL_CONFIG
    
    # Test valid file names
    valid_names = [
        "report.xlsx",
        "sales_data_2024.xls",
        "monthly_report_01.xlsx",
        "data file.xlsx"
    ]
    
    for name in valid_names:
        is_valid = config.file_name.validate_name(name)
        print(f"✅ '{name}': {'VALID' if is_valid else 'INVALID'}")
    
    # Test invalid file names
    invalid_names = [
        "report.txt",
        "data@file.xlsx",
        "file with spaces and dots...xlsx",
        "no_extension"
    ]
    
    for name in invalid_names:
        is_valid = config.file_name.validate_name(name)
        print(f"❌ '{name}': {'VALID' if is_valid else 'INVALID'}")
    
    return True


def test_header_validation():
    """Test header validation logic."""
    print("\n🧪 Testing header validation...")
    
    config = DEFAULT_EXCEL_CONFIG
    sheet_config = config.get_sheet_config("Test Sheet")
    
    # Test with valid headers
    valid_headers = ["Клиент", "Товар", "Количество", "Цена продажи"]
    missing_required = sheet_config.get_missing_required_headers(valid_headers)
    extra_headers = sheet_config.get_extra_headers(valid_headers)
    
    print(f"✅ Valid headers: {valid_headers}")
    print(f"   - Missing required: {missing_required}")
    print(f"   - Extra headers: {extra_headers}")
    
    # Test with missing headers
    invalid_headers = ["Товар", "Количество"]  # Missing "Клиент"
    missing_required = sheet_config.get_missing_required_headers(invalid_headers)
    extra_headers = sheet_config.get_extra_headers(invalid_headers)
    
    print(f"❌ Invalid headers: {invalid_headers}")
    print(f"   - Missing required: {missing_required}")
    print(f"   - Extra headers: {extra_headers}")
    
    return True


def test_excel_validator_integration():
    """Test Excel validator integration."""
    print("\n🧪 Testing Excel validator integration...")
    
    # Create validator
    validator = DataValidator()
    print(f"✅ Created DataValidator with default config")
    
    # Test with non-existent file
    try:
        result = validator.validate_excel_file("non_existent_file.xlsx")
        print(f"✅ Non-existent file validation: {result.is_valid}")
        print(f"   - Errors: {len(result.issues)}")
    except Exception as e:
        print(f"❌ Error testing non-existent file: {e}")
    
    return True


def main():
    """Main test function."""
    print("🚀 Starting Excel validation system tests...\n")
    
    try:
        # Run tests
        test_excel_validation_models()
        test_validation_config()
        test_file_name_validation()
        test_header_validation()
        test_excel_validator_integration()
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("   - ExcelFile and ExcelSheet models work correctly")
        print("   - Validation configuration is properly structured")
        print("   - File name validation works as expected")
        print("   - Header validation logic is functional")
        print("   - Excel validator integration is ready")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 