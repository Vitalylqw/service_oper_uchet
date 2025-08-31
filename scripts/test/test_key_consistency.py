#!/usr/bin/env python3
"""
Тест согласованности между deal_key и hash_key после добавления period.

Проверяет, что оба ключа включают period и работают корректно.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from domain.models.deal import Deal
from domain.value_objects.common import Period

def test_key_consistency():
    """Тестирует согласованность между deal_key и hash_key."""
    
    print("🧪 Тестирование согласованности ключей...")
    
    # Создаем период
    period = Period(
        month="Апрель", 
        year="2025", 
        full_name="Апрель 2025"
    )
    
    # Создаем две одинаковые сделки
    deal1 = Deal(
        client_name="ООО Консистенция",
        invoice_info="Счет № 456 от 20.04.2025",
        period=period
    )
    deal1.invoice_number = "456"
    deal1.invoice_date = "20.04.2025"
    deal1.seller = "Петров П.П."
    
    deal2 = Deal(
        client_name="ООО Консистенция",
        invoice_info="Счет № 456 от 20.04.2025",
        period=period
    )
    deal2.invoice_number = "456"
    deal2.invoice_date = "20.04.2025"
    deal2.seller = "Петров П.П."
    
    # Проверяем deal_key
    print(f"📋 deal_key сделки 1: {deal1.deal_key}")
    print(f"📋 deal_key сделки 2: {deal2.deal_key}")
    
    deal_keys_match = deal1.deal_key == deal2.deal_key
    print(f"✅ deal_key одинаковые: {deal_keys_match}")
    
    # Проверяем hash_key
    print(f"📋 hash_key сделки 1: {deal1.hash_key.value}")
    print(f"📋 hash_key сделки 2: {deal2.hash_key.value}")
    
    hash_keys_match = deal1.hash_key == deal2.hash_key
    print(f"✅ hash_key одинаковые: {hash_keys_match}")
    
    # Проверяем что period включен в deal_key
    period_in_deal_key = str(period) in deal1.deal_key
    print(f"✅ period включен в deal_key: {period_in_deal_key}")
    
    # Общий результат
    if deal_keys_match and hash_keys_match and period_in_deal_key:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ: ключи согласованы и включают period")
        return True
    else:
        print("❌ ЕСТЬ ПРОБЛЕМЫ С СОГЛАСОВАННОСТЬЮ КЛЮЧЕЙ")
        return False

def test_period_uniqueness():
    """Тестирует, что period делает ключи уникальными."""
    
    print("\n🧪 Тестирование уникальности по period...")
    
    # Создаем два разных периода
    period1 = Period(month="Май", year="2025", full_name="Май 2025")
    period2 = Period(month="Июнь", year="2025", full_name="Июнь 2025")
    
    # Создаем одинаковые сделки, но с разными периодами
    deal1 = Deal(
        client_name="ООО Уникальность",
        invoice_info="Счет № 789",
        period=period1
    )
    deal1.invoice_number = "789"
    deal1.seller = "Сидоров С.С."
    
    deal2 = Deal(
        client_name="ООО Уникальность",
        invoice_info="Счет № 789",
        period=period2
    )
    deal2.invoice_number = "789"
    deal2.seller = "Сидоров С.С."
    
    print(f"📋 deal_key для Мая: {deal1.deal_key}")
    print(f"📋 deal_key для Июня: {deal2.deal_key}")
    
    keys_different = deal1.deal_key != deal2.deal_key
    print(f"✅ deal_key разные для разных периодов: {keys_different}")
    
    # Проверяем hash_key тоже разные
    hash_different = deal1.hash_key != deal2.hash_key
    print(f"✅ hash_key разные для разных периодов: {hash_different}")
    
    if keys_different and hash_different:
        print("🎉 ТЕСТ ПРОЙДЕН: period обеспечивает уникальность ключей")
        return True
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: period не обеспечивает уникальность")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ СОГЛАСОВАННОСТИ КЛЮЧЕЙ С PERIOD")
    print("=" * 80)
    
    try:
        test1_passed = test_key_consistency()
        test2_passed = test_period_uniqueness()
        
        print("\n" + "=" * 80)
        if test1_passed and test2_passed:
            print("🎉 ВСЕ ТЕСТЫ СОГЛАСОВАННОСТИ ПРОЙДЕНЫ!")
            print("✅ deal_key и hash_key корректно работают с period")
            print("✅ period обеспечивает уникальность сделок")
            sys.exit(0)
        else:
            print("❌ НЕКОТОРЫЕ ТЕСТЫ СОГЛАСОВАННОСТИ НЕ ПРОЙДЕНЫ")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ ОШИБКА ПРИ ВЫПОЛНЕНИИ ТЕСТОВ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
