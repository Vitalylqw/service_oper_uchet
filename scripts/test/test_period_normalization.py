#!/usr/bin/env python3
"""
Test script for period normalization functionality.
Проверяет работу нормализаторов периодов в Period и DealItem.
"""

import sys
sys.path.append('/workspaces/service_oper_uchet')

from src.domain.value_objects.common import Period
from src.domain.models.deal import DealItem
from decimal import Decimal


def test_period_normalize_month():
    """Test Period.normalize_month with various inputs."""
    print("=== Testing Period.normalize_month ===")
    test_cases = [
        ("январь", "Январь"),
        ("ЯНВАРЬ", "Январь"),
        ("january", "Январь"),
        ("JANUARY", "Январь"),
        ("1", "Январь"),
        ("01", "Январь"),
        ("декабрь", "Декабрь"),
        ("december", "Декабрь"),
        ("12", "Декабрь"),
    ]
    
    for input_val, expected in test_cases:
        try:
            result = Period.normalize_month(input_val)
            status = "✓" if result == expected else "✗"
            print(f"{status} {input_val:10} → {result:10} (expected: {expected})")
        except Exception as e:
            print(f"✗ {input_val:10} → ERROR: {e}")
    
    # Test invalid inputs
    print("\n--- Testing invalid month inputs ---")
    invalid_cases = ["invalid", "13", "0", ""]
    for input_val in invalid_cases:
        try:
            result = Period.normalize_month(input_val)
            print(f"✗ {input_val:10} → {result} (should have failed)")
        except Exception as e:
            print(f"✓ {input_val:10} → ERROR (expected): {e}")


def test_period_normalize_year():
    """Test Period.normalize_year with various inputs."""
    print("\n=== Testing Period.normalize_year ===")
    test_cases = [
        ("24", "2024"),
        ("2024", "2024"),
        ("23", "2023"),
        ("2023", "2023"),
    ]
    
    for input_val, expected in test_cases:
        try:
            result = Period.normalize_year(input_val)
            status = "✓" if result == expected else "✗"
            print(f"{status} {input_val:10} → {result:10} (expected: {expected})")
        except Exception as e:
            print(f"✗ {input_val:10} → ERROR: {e}")
    
    # Test invalid inputs
    print("\n--- Testing invalid year inputs ---")
    invalid_cases = ["invalid", "9", "999", "2050", "2009"]
    for input_val in invalid_cases:
        try:
            result = Period.normalize_year(input_val)
            print(f"✗ {input_val:10} → {result} (should have failed)")
        except Exception as e:
            print(f"✓ {input_val:10} → ERROR (expected): {e}")


def test_period_from_sheet_name():
    """Test Period.from_sheet_name method."""
    print("\n=== Testing Period.from_sheet_name ===")
    test_cases = [
        ("Январь 2024", ("Январь", "2024")),
        ("январь 24", ("Январь", "2024")),
        ("January 2023", ("Январь", "2023")),
        ("декабрь 2025", ("Декабрь", "2025")),
    ]
    
    for sheet_name, (expected_month, expected_year) in test_cases:
        try:
            period = Period.from_sheet_name(sheet_name)
            month_ok = period.month == expected_month
            year_ok = period.year == expected_year
            status = "✓" if month_ok and year_ok else "✗"
            print(f"{status} '{sheet_name}' → month: {period.month}, year: {period.year}")
        except Exception as e:
            print(f"✗ '{sheet_name}' → ERROR: {e}")


def test_deal_item_validation():
    """Test DealItem period field validation."""
    print("\n=== Testing DealItem period validation ===")
    
    try:
        # Test valid period fields
        item = DealItem(
            product_name="Test Product",
            client_name="Test Client",
            period_month="январь",  # Should be normalized to "Январь"
            period_year="24",       # Should be normalized to "2024"
            seller="Test Seller",
            invoice_info="Test Invoice",
            deal_key="test-key",
            position_number=1
        )
        
        print(f"✓ Created DealItem with:")
        print(f"  period_month: '{item.period_month}' (normalized from 'январь')")
        print(f"  period_year: '{item.period_year}' (normalized from '24')")
        
    except Exception as e:
        print(f"✗ Failed to create DealItem: {e}")
    
    # Test invalid period fields
    print("\n--- Testing invalid period fields ---")
    try:
        invalid_item = DealItem(
            product_name="Test Product",
            client_name="Test Client",
            period_month="invalid_month",
            period_year="24",
            seller="Test Seller",
            invoice_info="Test Invoice",
            deal_key="test-key",
            position_number=1
        )
        print(f"✗ Should have failed with invalid month")
    except Exception as e:
        print(f"✓ Correctly failed with invalid month: {e}")


if __name__ == "__main__":
    print("Testing Period Normalization Functionality\n")
    
    test_period_normalize_month()
    test_period_normalize_year()
    test_period_from_sheet_name()
    test_deal_item_validation()
    
    print("\n=== Test completed ===")
