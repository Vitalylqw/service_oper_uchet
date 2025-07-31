#!/usr/bin/env python3
"""
Скрипт для принудительного обновления CSS и проверки Dashboard layout.
"""

import requests
import time
import webbrowser


def check_css_changes():
    """Проверяет CSS файл на наличие изменений."""
    try:
        # Проверяем, что React dev server работает
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ React dev server работает")
        else:
            print(f"❌ React dev server вернул статус: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ React dev server недоступен: {e}")
        return False
    
    return True


def force_refresh_instructions():
    """Выводит инструкции для принудительного обновления."""
    print("\n🔄 ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ CSS")
    print("=" * 50)
    print("1. Откройте http://localhost:3000/dashboard")
    print("2. Войдите с данными: viewer/password")
    print("3. Нажмите F12 (Developer Tools)")
    print("4. Щелкните правой кнопкой по кнопке обновления")
    print("5. Выберите 'Очистить кеш и жесткая перезагрузка'")
    print("   (Empty Cache and Hard Reload)")
    print()
    print("🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("- 4 статистические карточки в одну строку")
    print("- 'Последние сделки' СЛЕВА")
    print("- 'Синхронизация' СПРАВА")
    print("- Секции на ОДНОМ УРОВНЕ под карточками")
    print()
    print("💡 Если проблема остается:")
    print("- Проверьте ширину экрана (должна быть >900px)")
    print("- Попробуйте другой браузер")
    print("- Проверьте Console на ошибки CSS")


def create_css_verification():
    """Создает CSS для проверки изменений."""
    css_verification = """
/* ПРОВЕРОЧНЫЕ СТИЛИ - добавьте в конец Dashboard.css */

/* Подсветка для отладки */
.debug-highlight .stats-grid {
    border: 3px solid red !important;
    background: rgba(255, 0, 0, 0.1) !important;
}

.debug-highlight .dashboard-content {
    border: 3px solid blue !important;
    background: rgba(0, 0, 255, 0.1) !important;
}

.debug-highlight .dashboard-section:first-child {
    border: 3px solid green !important;
    background: rgba(0, 255, 0, 0.1) !important;
}

.debug-highlight .dashboard-section:last-child {
    border: 3px solid orange !important;
    background: rgba(255, 165, 0, 0.1) !important;
}

/* Принудительный CSS для layout */
.force-layout .dashboard-content {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 24px !important;
    align-items: start !important;
}

.force-layout .stats-grid {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 16px !important;
    margin-bottom: 32px !important;
    max-width: 1200px !important;
}
"""
    
    with open('css_verification.css', 'w', encoding='utf-8') as f:
        f.write(css_verification)
    
    print("\n📝 Создан файл css_verification.css")
    print("Можно добавить эти стили для принудительного применения layout")


def main():
    """Основная функция."""
    print("🔄 ПРОВЕРКА И ОБНОВЛЕНИЕ CSS DASHBOARD")
    print("=" * 60)
    
    if check_css_changes():
        force_refresh_instructions()
        create_css_verification()
        
        # Открываем Dashboard
        try:
            webbrowser.open("http://localhost:3000/dashboard")
            print("\n🌐 Dashboard открыт в браузере")
        except Exception as e:
            print(f"\n⚠️ Не удалось открыть браузер: {e}")
    
    print("\n" + "=" * 60)
    print("📋 ДИАГНОСТИКА:")
    print("- Если секции все еще вертикальные, проверьте ширину экрана")
    print("- Если карточки переносятся, очистите кеш браузера")
    print("- При проблемах попробуйте режим инкогнито")


if __name__ == "__main__":
    main()