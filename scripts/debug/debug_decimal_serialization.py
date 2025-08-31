#!/usr/bin/env python3
"""
Debug script to reproduce Decimal serialization issue.

This script will help identify exactly where Decimal objects 
are ending up in event_data during synchronization.
"""

import sys
import os
import json
from decimal import Decimal
from typing import Any, Dict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from domain.models import Deal, DealItem
from domain.value_objects import Period, Money, SignedMoney, Status


def find_decimal_in_dict(data: Dict[str, Any], path: str = "") -> list[str]:
    """Recursively find all Decimal objects in a dictionary."""
    decimal_paths = []
    
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        
        if isinstance(value, Decimal):
            decimal_paths.append(f"{current_path}: {value} ({type(value)})")
        elif isinstance(value, dict):
            decimal_paths.extend(find_decimal_in_dict(value, current_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, Decimal):
                    decimal_paths.append(f"{current_path}[{i}]: {item} ({type(item)})")
                elif isinstance(item, dict):
                    decimal_paths.extend(find_decimal_in_dict(item, f"{current_path}[{i}]"))
    
    return decimal_paths


def test_deal_serialization():
    """Test Deal object serialization to find Decimal issues."""
    print("🔍 Testing Deal object serialization...")
    
    # Create test deal with financial data
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    
    deal = Deal(
        client_name="ООО Тест Клиент",
        invoice_info="Счет 12345 от 15.01.2024",
        invoice_number="12345",
        invoice_date="15.01.2024",
        period=period,
        seller="Иванов И.И.",
        is_shipped=Status.SHIPPED,
        is_paid=Status.PENDING,
        total_revenue=Money(amount=Decimal("50000.00")),
        total_margin=SignedMoney(amount=Decimal("15000.00")),
        total_cost=Money(amount=Decimal("35000.00")),
        kickback_amount=Money(amount=Decimal("2500.00"))
    )
    
    print(f"✅ Deal created: {deal.deal_key}")
    
    # Test direct dict conversion
    try:
        deal_dict = deal.model_dump()
        print("✅ deal.model_dump() completed")
        
        # Look for Decimals in the dict
        decimal_paths = find_decimal_in_dict(deal_dict)
        if decimal_paths:
            print("❌ Found Decimal objects in deal.model_dump():")
            for path in decimal_paths:
                print(f"  - {path}")
        else:
            print("✅ No Decimal objects found in deal.model_dump()")
            
    except Exception as e:
        print(f"❌ deal.model_dump() failed: {e}")
    
    # Test JSON serialization
    try:
        deal_json = deal.model_dump_json()
        print("✅ deal.model_dump_json() completed")
    except Exception as e:
        print(f"❌ deal.model_dump_json() failed: {e}")
    
    # Test manual dict creation (like in orchestrator)
    try:
        manual_dict = {
            "deal_id": str(deal.id),
            "deal_key": deal.deal_key,
            "client_name": deal.client_name,
            "total_revenue": str(deal.total_revenue.amount) if deal.total_revenue else None,
            "total_margin": str(deal.total_margin.amount) if deal.total_margin else None,
            "total_cost": str(deal.total_cost.amount) if deal.total_cost else None,
            "kickback_amount": str(deal.kickback_amount.amount) if deal.kickback_amount else None,
        }
        
        print("✅ Manual dict creation completed")
        
        # Test JSON serialization of manual dict
        manual_json = json.dumps(manual_dict)
        print("✅ Manual dict JSON serialization completed")
        
    except Exception as e:
        print(f"❌ Manual dict creation/serialization failed: {e}")
    
    return deal


def test_field_changes_simulation():
    """Simulate field_changes creation like in change detector."""
    print("\n🔍 Testing field_changes simulation...")
    
    # Create two deals with different financial data
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    
    old_deal = Deal(
        client_name="ООО Тест Клиент",
        invoice_info="Счет 12345 от 15.01.2024",
        invoice_number="12345",
        invoice_date="15.01.2024",
        period=period,
        seller="Иванов И.И.",
        total_revenue=Money(amount=Decimal("45000.00")),
        total_margin=SignedMoney(amount=Decimal("12000.00")),
        total_cost=Money(amount=Decimal("33000.00")),
    )
    
    new_deal = Deal(
        client_name="ООО Тест Клиент",
        invoice_info="Счет 12345 от 15.01.2024",
        invoice_number="12345",
        invoice_date="15.01.2024",
        period=period,
        seller="Иванов И.И.",
        total_revenue=Money(amount=Decimal("50000.00")),
        total_margin=SignedMoney(amount=Decimal("15000.00")),
        total_cost=Money(amount=Decimal("35000.00")),
    )
    
    # Simulate _compare_deal_fields logic
    changes = {}
    money_fields = ["total_revenue", "total_margin", "total_cost", "kickback_amount"]
    
    for field in money_fields:
        old_money = getattr(old_deal, field, None)
        new_money = getattr(new_deal, field, None)
        
        old_amount = str(old_money.amount) if old_money else None
        new_amount = str(new_money.amount) if new_money else None
        
        if old_amount != new_amount:
            changes[field] = {"old_value": old_amount, "new_value": new_amount}
    
    print(f"✅ Field changes created: {changes}")
    
    # Test JSON serialization
    try:
        changes_json = json.dumps(changes)
        print("✅ Field changes JSON serialization completed")
        
        # Look for Decimals
        decimal_paths = find_decimal_in_dict(changes)
        if decimal_paths:
            print("❌ Found Decimal objects in field_changes:")
            for path in decimal_paths:
                print(f"  - {path}")
        else:
            print("✅ No Decimal objects found in field_changes")
            
    except Exception as e:
        print(f"❌ Field changes JSON serialization failed: {e}")
    
    return changes


def test_event_creation():
    """Test full event creation like in orchestrator."""
    print("\n🔍 Testing event creation...")
    
    deal = test_deal_serialization()
    field_changes = test_field_changes_simulation()
    
    # Create DealUpdated event like in orchestrator
    event = {
        "aggregate_id": deal.id,
        "event_type": "DealUpdated",
        "event_data": {
            "deal_id": str(deal.id),
            "deal_key": deal.deal_key,
            "field_changes": field_changes,
            "client_name": deal.client_name,
            "total_revenue": str(deal.total_revenue.amount) if deal.total_revenue else None,
            "total_margin": str(deal.total_margin.amount) if deal.total_margin else None,
            "total_cost": str(deal.total_cost.amount) if deal.total_cost else None,
            "kickback_amount": str(deal.kickback_amount.amount) if deal.kickback_amount else None,
        }
    }
    
    print("✅ Event created")
    
    # Test JSON serialization
    try:
        event_json = json.dumps(event, default=str)
        print("✅ Event JSON serialization completed")
        
        # Look for Decimals in event
        decimal_paths = find_decimal_in_dict(event)
        if decimal_paths:
            print("❌ Found Decimal objects in event:")
            for path in decimal_paths:
                print(f"  - {path}")
        else:
            print("✅ No Decimal objects found in event")
            
    except Exception as e:
        print(f"❌ Event JSON serialization failed: {e}")


def main():
    """Main test function."""
    print("=" * 60)
    print("🔬 DECIMAL SERIALIZATION DEBUG")
    print("=" * 60)
    
    try:
        test_deal_serialization()
        test_field_changes_simulation()
        test_event_creation()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
