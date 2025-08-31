#!/usr/bin/env python3
"""
Test script for deterministic ID generation.

Verifies that Deal and DealItem IDs are generated deterministically 
based on their business keys.
"""

import sys
import os
from uuid import UUID
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from domain.models import Deal, DealItem
from domain.value_objects import Period, Money, SignedMoney, Status


def test_deterministic_deal_ids():
    """Test that Deal IDs are deterministic based on deal_key."""
    print("🔬 Testing deterministic Deal IDs...")
    
    # Create two identical deals
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    
    deal1 = Deal(
        client_name="ООО Тест Клиент",
        invoice_info="Счет 12345 от 15.01.2024",
        invoice_number="12345",
        invoice_date="15.01.2024",
        seller="Иванов И.И.",
        period=period,
        is_shipped=Status.COMPLETED,
        is_paid=Status.PENDING,
        total_revenue=Money(amount=Decimal("1000.00")),
        total_margin=SignedMoney(amount=Decimal("200.00")),
        total_cost=Money(amount=Decimal("800.00"))
    )
    
    deal2 = Deal(
        client_name="ООО Тест Клиент",
        invoice_info="Счет 12345 от 15.01.2024",
        invoice_number="12345",
        invoice_date="15.01.2024",
        seller="Иванов И.И.",
        period=period,
        is_shipped=Status.COMPLETED,
        is_paid=Status.PENDING,
        total_revenue=Money(amount=Decimal("1000.00")),
        total_margin=SignedMoney(amount=Decimal("200.00")),
        total_cost=Money(amount=Decimal("800.00"))
    )
    
    # Check that IDs are identical
    print(f"Deal 1 ID: {deal1.id}")
    print(f"Deal 2 ID: {deal2.id}")
    print(f"Deal 1 deal_key: {deal1.deal_key}")
    print(f"Deal 2 deal_key: {deal2.deal_key}")
    
    assert deal1.id == deal2.id, "Identical deals should have same ID"
    assert deal1.deal_key == deal2.deal_key, "Identical deals should have same deal_key"
    
    # Create a different deal
    deal3 = Deal(
        client_name="ООО Другой Клиент",  # Different client
        invoice_info="Счет 12346 от 16.01.2024",
        invoice_number="12346",
        invoice_date="16.01.2024",
        seller="Петров П.П.",
        period=period
    )
    
    print(f"Deal 3 ID: {deal3.id}")
    print(f"Deal 3 deal_key: {deal3.deal_key}")
    
    assert deal3.id != deal1.id, "Different deals should have different IDs"
    assert deal3.deal_key != deal1.deal_key, "Different deals should have different deal_keys"
    
    print("✅ Deal ID tests passed!")


def test_deterministic_item_ids():
    """Test that DealItem IDs are deterministic based on deal_id + position_number + product_name."""
    print("\n🔬 Testing deterministic DealItem IDs...")
    
    # Create a deal first
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    deal = Deal(
        client_name="ООО Тест Клиент",
        invoice_info="Счет 12345 от 15.01.2024",
        period=period
    )
    
    # Create two identical items
    item1 = DealItem(
        deal_id=deal.id,
        product_name="Товар А",
        supplier_name="Поставщик 1",
        position_number=1,
        quantity=Decimal("10.0"),
        purchase_price=Money(amount=Decimal("100.00")),
        sale_price=Money(amount=Decimal("120.00"))
    )
    
    item2 = DealItem(
        deal_id=deal.id,
        product_name="Товар А",
        supplier_name="Поставщик 1", 
        position_number=1,
        quantity=Decimal("10.0"),
        purchase_price=Money(amount=Decimal("100.00")),
        sale_price=Money(amount=Decimal("120.00"))
    )
    
    print(f"Item 1 ID: {item1.id}")
    print(f"Item 2 ID: {item2.id}")
    print(f"Item 1 deal_id: {item1.deal_id}")
    print(f"Item 2 deal_id: {item2.deal_id}")
    
    assert item1.id == item2.id, "Identical items should have same ID"
    
    # Create a different item (different position)
    item3 = DealItem(
        deal_id=deal.id,
        product_name="Товар А",
        supplier_name="Поставщик 1",
        position_number=2,  # Different position
        quantity=Decimal("10.0"),
        purchase_price=Money(amount=Decimal("100.00")),
        sale_price=Money(amount=Decimal("120.00"))
    )
    
    print(f"Item 3 ID: {item3.id}")
    
    assert item3.id != item1.id, "Items with different positions should have different IDs"
    
    # Create item with different product
    item4 = DealItem(
        deal_id=deal.id,
        product_name="Товар Б",  # Different product
        supplier_name="Поставщик 1",
        position_number=1,
        quantity=Decimal("10.0"),
        purchase_price=Money(amount=Decimal("100.00")),
        sale_price=Money(amount=Decimal("120.00"))
    )
    
    print(f"Item 4 ID: {item4.id}")
    
    assert item4.id != item1.id, "Items with different products should have different IDs"
    
    print("✅ DealItem ID tests passed!")


def test_stability_across_recreations():
    """Test that IDs remain stable across multiple object recreations."""
    print("\n🔬 Testing ID stability across recreations...")
    
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    
    # Create same deal 10 times
    ids = []
    for i in range(10):
        deal = Deal(
            client_name="ООО Стабильность",
            invoice_info="Счет 99999 от 01.01.2024",
            invoice_number="99999",
            invoice_date="01.01.2024",
            period=period
        )
        ids.append(deal.id)
    
    # All IDs should be identical
    unique_ids = set(ids)
    print(f"Generated {len(ids)} deals, got {len(unique_ids)} unique IDs")
    print(f"Stable ID: {ids[0]}")
    
    assert len(unique_ids) == 1, "All recreated deals should have same ID"
    
    print("✅ Stability tests passed!")


def test_manual_id_override():
    """Test that manual ID setting works correctly."""
    print("\n🔬 Testing manual ID override...")
    
    period = Period(month="Январь", year="2024", full_name="Январь 2024")
    
    deal = Deal(
        client_name="ООО Тест",
        invoice_info="Счет тест",
        period=period
    )
    
    original_id = deal.id
    print(f"Original deterministic ID: {original_id}")
    
    # Set manual ID
    manual_id = UUID('12345678-1234-5678-9abc-123456789012')
    deal.set_id(manual_id)
    
    print(f"Manual ID: {deal.id}")
    assert deal.id == manual_id, "Manual ID should override deterministic one"
    
    # Create new deal with same data - should have original deterministic ID
    deal2 = Deal(
        client_name="ООО Тест",
        invoice_info="Счет тест",
        period=period
    )
    
    print(f"New deal ID: {deal2.id}")
    assert deal2.id == original_id, "New deal should have deterministic ID"
    assert deal2.id != manual_id, "New deal should not have manual ID"
    
    print("✅ Manual ID override tests passed!")


def main():
    """Run all tests."""
    print("🚀 Starting deterministic ID tests...\n")
    
    try:
        test_deterministic_deal_ids()
        test_deterministic_item_ids() 
        test_stability_across_recreations()
        test_manual_id_override()
        
        print("\n🎉 All tests passed! Deterministic IDs are working correctly!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
