#!/usr/bin/env python3
"""
Тест для проверки нового формата deal_key с добавлением period.

Проверяет, что deal_key теперь включает period в конкатенацию.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from domain.models.deal import Deal
from domain.value_objects.common import Period

def test_deal_key_with_period():
    """Тестирует новый формат deal_key с period."""
    
    print("🧪 Тестирование нового формата deal_key с period...")
    
    # Создаем период
    period = Period(
        month="Январь", 
        year="2025", 
        full_name="Январь 2025"
    )
    
    # Создаем сделку
    deal = Deal(
        client_name="ООО Тестовый клиент",
        invoice_info="Счет № 123 от 15.01.2025",
        period=period
    )
    
    # Устанавливаем дополнительные поля
    deal.invoice_number = "123"
    deal.invoice_date = "15.01.2025"
    deal.seller = "Иванов И.И."
    
    # Получаем deal_key
    deal_key = deal.deal_key
    
    print(f"📋 Сформированный deal_key: {deal_key}")
    
    # Проверяем формат
    expected_parts = [
        "ООО Тестовый клиент",
        "123", 
        "15.01.2025",
        "Иванов И.И.",
        "Январь 2025"  # period должен быть в конце
    ]
    expected_key = "|".join(expected_parts)
    
    print(f"📋 Ожидаемый deal_key: {expected_key}")
    
    # Проверяем соответствие
    if deal_key == expected_key:
        print("✅ ТЕСТ ПРОЙДЕН: deal_key содержит period в правильном формате")
        return True
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: deal_key не соответствует ожидаемому формату")
        print(f"   Получено: {deal_key}")
        print(f"   Ожидалось: {expected_key}")
        return False

def test_deal_key_with_empty_fields():
    """Тестирует deal_key с пустыми полями."""
    
    print("\n🧪 Тестирование deal_key с пустыми полями...")
    
    # Создаем период
    period = Period(
        month="Февраль", 
        year="2025", 
        full_name="Февраль 2025"
    )
    
    # Создаем сделку с минимальными данными
    deal = Deal(
        client_name="ООО Клиент",
        invoice_info="Минимальная информация",
        period=period
    )
    
    # Получаем deal_key (invoice_number, invoice_date, seller будут пустыми)
    deal_key = deal.deal_key
    
    print(f"📋 deal_key с пустыми полями: {deal_key}")
    
    # Проверяем формат (пустые поля должны быть как пустые строки между |)
    expected_key = "ООО Клиент||||Февраль 2025"
    
    if deal_key == expected_key:
        print("✅ ТЕСТ ПРОЙДЕН: deal_key правильно обрабатывает пустые поля")
        return True
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: неправильная обработка пустых полей")
        print(f"   Получено: {deal_key}")
        print(f"   Ожидалось: {expected_key}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ НОВОГО ФОРМАТА deal_key С PERIOD")
    print("=" * 80)
    
    try:
        test1_passed = test_deal_key_with_period()
        test2_passed = test_deal_key_with_empty_fields()
        
        print("\n" + "=" * 80)
        if test1_passed and test2_passed:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ deal_key теперь включает period в конкатенацию")
            sys.exit(0)
        else:
            print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ ОШИБКА ПРИ ВЫПОЛНЕНИИ ТЕСТОВ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
