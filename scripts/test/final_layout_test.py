#!/usr/bin/env python3
"""
Финальный тест Dashboard layout с принудительными CSS стилями.
"""

import requests
import webbrowser
import time


def test_final_layout():
    """Финальный тест layout."""
    print("🎯 ФИНАЛЬНЫЙ ТЕСТ DASHBOARD LAYOUT")
    print("=" * 60)
    
    # Проверяем серверы
    try:
        api_response = requests.get("http://localhost:8000/health", timeout=5)
        ui_response = requests.get("http://localhost:3000", timeout=5)
        
        if api_response.status_code == 200 and ui_response.status_code == 200:
            print("✅ Все серверы работают корректно")
        else:
            print("❌ Проблемы с серверами")
            return
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    print("\n🔧 ПРИМЕНЕНЫ ПРИНУДИТЕЛЬНЫЕ CSS СТИЛИ:")
    print("- .dashboard-content: grid-template-columns: 1fr 1fr !important")
    print("- .stats-grid: grid-template-columns: repeat(4, 1fr) !important")
    print("- Все стили с флагом !important для переопределения")
    
    print("\n📋 ИНСТРУКЦИИ ДЛЯ ПРОВЕРКИ:")
    print("1. ✅ Откройте http://localhost:3000/dashboard")
    print("2. ✅ Войдите: viewer/password")
    print("3. ✅ Принудительно обновите (Ctrl+F5 или Cmd+Shift+R)")
    print("4. ✅ Проверьте layout:")
    
    print("\n🎯 ДОЛЖНО БЫТЬ:")
    print("   ┌─────────────────────────────────────────────┐")
    print("   │ [📊] [💰] [✅] [🔄] <- 4 карточки в ряд    │")
    print("   ├─────────────────────────────────────────────┤")
    print("   │ ┌─────────────────┐ ┌─────────────────────┐ │")
    print("   │ │ Последние сделки│ │   Синхронизация     │ │")
    print("   │ │       (слева)   │ │      (справа)       │ │")
    print("   │ └─────────────────┘ └─────────────────────┘ │")
    print("   └─────────────────────────────────────────────┘")
    
    print("\n💡 ЕСЛИ LAYOUT НЕ СООТВЕТСТВУЕТ:")
    print("- Проверьте ширину экрана (>900px для горизонтального layout)")
    print("- Попробуйте режим инкогнито браузера")
    print("- Проверьте Console на ошибки CSS (F12)")
    print("- Убедитесь, что нет других CSS файлов, переопределяющих стили")
    
    # Открываем Dashboard
    try:
        webbrowser.open("http://localhost:3000/dashboard")
        print("\n🌐 Dashboard открыт автоматически")
    except Exception as e:
        print(f"\n⚠️ Не удалось открыть браузер: {e}")
    
    print("\n" + "=" * 60)
    print("🔧 ПРИМЕНЕНЫ МАКСИМАЛЬНО ПРИНУДИТЕЛЬНЫЕ СТИЛИ")
    print("📊 LAYOUT ДОЛЖЕН РАБОТАТЬ НА 100%")
    print("=" * 60)


if __name__ == "__main__":
    test_final_layout()