#!/usr/bin/env python3
"""
Test script for Deal and DealItem serialization.

Tests the unified string serialization for Money fields.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from decimal import Decimal
from datetime import datetime, timezone

from domain.models.deal import Deal, DealItem
from domain.value_objects import Money, SignedMoney, Period, Status


def test_deal_item_serialization():
    """Test DealItem serialization returns strings for Money fields."""
    print("🔍 Testing DealItem serialization...")
    
    item = DealItem(
        product_name="Test Product",
        client_name="Test Client", 
        period_month="Январь",
        period_year="2024",
        seller="Test Seller",
        invoice_info="Test Invoice",
        deal_key="test_key",
        position_number=1,
        quantity=Decimal("10.00"),
        purchase_price=Money(amount=Decimal("100.50")),
        sale_price=Money(amount=Decimal("150.75")),
        revenue=Money(amount=Decimal("1507.50")),
        cost=Money(amount=Decimal("1005.00")),
        margin=SignedMoney(amount=Decimal("502.50"))
    )
    
    # Test serialization
    data = item.model_dump()
    
    # Check Money fields are strings
    money_fields = ['purchase_price', 'sale_price', 'revenue', 'cost']
    for field in money_fields:
        value = data.get(field)
        print(f"  {field}: {value} (type: {type(value)})")
        assert isinstance(value, str), f"Expected string for {field}, got {type(value)}"
    
    # Check SignedMoney field is string  
    margin_value = data.get('margin')
    print(f"  margin: {margin_value} (type: {type(margin_value)})")
    assert isinstance(margin_value, str), f"Expected string for margin, got {type(margin_value)}"
    
    print("✅ DealItem serialization test passed!")
    return True


def test_deal_serialization():
    """Test Deal serialization returns strings for Money fields."""
    print("🔍 Testing Deal serialization...")
    
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    
    deal = Deal(
        client_name="Test Client",
        invoice_info="Test Invoice Info",
        invoice_number="INV-001",
        invoice_date="01.01.2024",
        period=period,
        seller="Test Seller",
        total_revenue=Money(amount=Decimal("50000.00")),
        total_margin=SignedMoney(amount=Decimal("15000.00")),
        total_cost=Money(amount=Decimal("35000.00")),
        kickback_amount=Money(amount=Decimal("2500.00"))
    )
    
    # Test serialization
    data = deal.model_dump()
    
    # Check Money fields are strings
    money_fields = ['total_revenue', 'total_cost', 'kickback_amount']
    for field in money_fields:
        value = data.get(field)
        print(f"  {field}: {value} (type: {type(value)})")
        assert isinstance(value, str), f"Expected string for {field}, got {type(value)}"
    
    # Check SignedMoney field is string
    margin_value = data.get('total_margin')
    print(f"  total_margin: {margin_value} (type: {type(margin_value)})")
    assert isinstance(margin_value, str), f"Expected string for total_margin, got {type(margin_value)}"
    
    print("✅ Deal serialization test passed!")
    return True


def main():
    """Run all serialization tests."""
    print("🚀 Testing unified string serialization for Money fields...")
    print()
    
    try:
        test_deal_item_serialization()
        print()
        test_deal_serialization()
        print()
        print("🎉 All serialization tests passed! Money fields are consistently serialized as strings.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

