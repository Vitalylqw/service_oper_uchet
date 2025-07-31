#!/usr/bin/env python3
"""
Проверка применения CSS изменений в Dashboard.
"""

import webbrowser


def check_css_applied():
    """Проверяет, что CSS изменения применились."""
    print("🔍 ПРОВЕРКА ПРИМЕНЕНИЯ CSS ИЗМЕНЕНИЙ")
    print("=" * 60)
    
    # Читаем CSS файл для проверки
    css_path = "src/presentation/web/src/components/dashboard/Dashboard.css"
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Проверяем наличие ключевых изменений
        checks = [
            ("grid-template-columns: 1fr 1fr !important", "✅ Горизонтальный layout секций"),
            ("grid-template-columns: repeat(4, 1fr) !important", "✅ 4 колонки статистики"),
            ("max-width: 900px", "✅ Медиа-запрос для адаптивности"),
            ("ПРИНУДИТЕЛЬНЫЕ СТИЛИ", "✅ Принудительные стили добавлены")
        ]
        
        print("📋 ПРОВЕРКА CSS ФАЙЛА:")
        all_good = True
        for check, description in checks:
            if check in css_content:
                print(f"  {description}")
            else:
                print(f"  ❌ НЕ НАЙДЕНО: {check}")
                all_good = False
        
        if all_good:
            print("\n✅ ВСЕ CSS ИЗМЕНЕНИЯ ПРИСУТСТВУЮТ В ФАЙЛЕ")
        else:
            print("\n❌ НЕКОТОРЫЕ CSS ИЗМЕНЕНИЯ ОТСУТСТВУЮТ")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка чтения CSS файла: {e}")
        return False
    
    print("\n🚀 ФИНАЛЬНАЯ ПРОВЕРКА В БРАУЗЕРЕ:")
    print("1. Откройте http://localhost:3000/dashboard")
    print("2. Принудительно обновите (Ctrl+F5)")
    print("3. Проверьте Developer Tools (F12):")
    print("   - Во вкладке Elements найдите .dashboard-content")
    print("   - Убедитесь, что grid-template-columns: 1fr 1fr")
    print("   - Найдите .stats-grid")
    print("   - Убедитесь, что grid-template-columns: repeat(4, 1fr)")
    
    print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("   ┌─────────────────────────────────────────┐")
    print("   │  📊    💰    ✅    🔄  ← В ОДНУ СТРОКУ │")
    print("   ├─────────────────────────────────────────┤")
    print("   │ ┌─────────────┐  ┌─────────────────────┐ │")
    print("   │ │ Последние   │  │   Синхронизация     │ │")
    print("   │ │  сделки     │  │                     │ │")
    print("   │ │   (СЛЕВА)   │  │      (СПРАВА)       │ │")
    print("   │ └─────────────┘  └─────────────────────┘ │")
    print("   └─────────────────────────────────────────┘")
    
    # Открываем Dashboard
    try:
        webbrowser.open("http://localhost:3000/dashboard")
        print("\n🌐 Dashboard открыт для проверки")
    except Exception as e:
        print(f"\n⚠️ Не удалось открыть браузер: {e}")
    
    return True


if __name__ == "__main__":
    if check_css_applied():
        print("\n" + "=" * 60)
        print("📊 CSS ИЗМЕНЕНИЯ ПРИМЕНЕНЫ")
        print("🎯 ПРОВЕРЬТЕ РЕЗУЛЬТАТ В БРАУЗЕРЕ")
        print("=" * 60)