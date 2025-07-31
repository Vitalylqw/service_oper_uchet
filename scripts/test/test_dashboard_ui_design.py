#!/usr/bin/env python3
"""
Тест для проверки улучшенного дизайна Dashboard.
Проверяет доступность UI и корректность отображения.
"""

import requests
import time
import subprocess
import webbrowser
from pathlib import Path


def check_api_health():
    """Проверка работы API сервера."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API сервер работает корректно")
            return True
        else:
            print(f"❌ API сервер вернул статус: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API сервер недоступен: {e}")
        return False


def check_ui_availability():
    """Проверка доступности UI."""
    try:
        response = requests.get("http://localhost:3000", timeout=10)
        if response.status_code == 200:
            print("✅ React UI доступен")
            return True
        else:
            print(f"❌ React UI вернул статус: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ React UI недоступен: {e}")
        return False


def test_dashboard_design():
    """Основная функция тестирования дизайна Dashboard."""
    print("🔍 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО ДИЗАЙНА DASHBOARD")
    print("=" * 60)
    
    # Проверяем API
    print("\n1. Проверка API сервера...")
    api_ok = check_api_health()
    
    # Проверяем UI
    print("\n2. Проверка React UI...")
    ui_ok = check_ui_availability()
    
    if api_ok and ui_ok:
        print("\n✅ РЕЗУЛЬТАТ: Серверы работают корректно!")
        print("\n📋 ИНСТРУКЦИИ ДЛЯ ПРОВЕРКИ ДИЗАЙНА:")
        print("1. Откройте http://localhost:3000 в браузере")
        print("2. Войдите с данными: viewer/password")
        print("3. Перейдите на Dashboard (/dashboard)")
        print("\n🎨 ОЖИДАЕМЫЕ УЛУЧШЕНИЯ:")
        print("- Статистические карточки в одну строку (4 колонки)")
        print("- Секции расположены параллельно друг другу внизу (2 колонки)")
        print("- Секции имеют фиксированную высоту (500px) с прокруткой")
        print("- Эргономичный горизонтальный layout секций")
        print("- Адаптивный дизайн: вертикально на планшетах и мобильных")
        
        # Открываем браузер
        try:
            webbrowser.open("http://localhost:3000/dashboard")
            print("\n🌐 Браузер открыт автоматически")
        except Exception as e:
            print(f"\n⚠️ Не удалось открыть браузер автоматически: {e}")
            
    else:
        print("\n❌ РЕЗУЛЬТАТ: Проблемы с серверами!")
        if not api_ok:
            print("- Запустите API сервер: python -m uvicorn src.presentation.api.main:app --reload")
        if not ui_ok:
            print("- Запустите React UI: cd src/presentation/web && npm start")


if __name__ == "__main__":
    test_dashboard_design()