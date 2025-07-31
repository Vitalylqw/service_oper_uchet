#!/usr/bin/env python3
"""
Отладочный тест для проверки layout Dashboard.
Создает HTML файл для визуальной проверки.
"""

def create_debug_html():
    """Создает отладочный HTML файл."""
    
    html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Layout Debug</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: #f8f9fa;
        }
        
        .debug-info {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }
        
        .screen-width {
            font-weight: bold;
            color: #856404;
        }
        
        /* Копируем основные стили Dashboard */
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 16px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
            max-width: 1200px;
        }
        
        .stats-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            text-align: center;
            min-height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .dashboard-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            align-items: start;
        }
        
        .dashboard-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            max-height: 500px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            min-height: 200px;
        }
        
        .section-title {
            font-weight: bold;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        /* Медиа-запросы */
        @media (max-width: 900px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            }
            
            .dashboard-content {
                grid-template-columns: 1fr;
                gap: 20px;
            }
        }
        
        @media (max-width: 768px) {
            .dashboard {
                padding: 0 8px;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-bottom: 20px;
            }
        }
        
        @media (max-width: 480px) {
            .stats-grid {
                grid-template-columns: 1fr;
                gap: 12px;
            }
        }
        
        .current-layout {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="debug-info">
        <div class="screen-width">Ширина экрана: <span id="screenWidth"></span>px</div>
        <div>Высота экрана: <span id="screenHeight"></span>px</div>
    </div>
    
    <div class="current-layout" id="layoutInfo">
        Определяется...
    </div>
    
    <div class="dashboard">
        <h1>Dashboard Layout Test</h1>
        
        <!-- Статистические карточки -->
        <div class="stats-grid">
            <div class="stats-card">📊 Карточка 1</div>
            <div class="stats-card">💰 Карточка 2</div>
            <div class="stats-card">✅ Карточка 3</div>
            <div class="stats-card">🔄 Карточка 4</div>
        </div>
        
        <!-- Секции контента -->
        <div class="dashboard-content">
            <div class="dashboard-section">
                <div class="section-title">Последние сделки</div>
                <div>• Сделка 1</div>
                <div>• Сделка 2</div>
                <div>• Сделка 3</div>
                <div>• Сделка 4</div>
                <div>• Сделка 5</div>
            </div>
            
            <div class="dashboard-section">
                <div class="section-title">Синхронизация</div>
                <div>• Сессия 1</div>
                <div>• Сессия 2</div>
                <div>• Сессия 3</div>
                <div>• Сессия 4</div>
                <div>• Сессия 5</div>
            </div>
        </div>
    </div>
    
    <script>
        function updateScreenInfo() {
            const width = window.innerWidth;
            const height = window.innerHeight;
            
            document.getElementById('screenWidth').textContent = width;
            document.getElementById('screenHeight').textContent = height;
            
            let layoutInfo = '';
            if (width > 900) {
                layoutInfo = '🖥️ ДЕСКТОП: 4 карточки в ряд + секции горизонтально';
            } else if (width > 768) {
                layoutInfo = '📱 ПЛАНШЕТ: 2×2 карточки + секции вертикально';
            } else if (width > 480) {
                layoutInfo = '📱 МОБИЛЬНЫЙ: 2×2 карточки + секции вертикально';
            } else {
                layoutInfo = '📱 МАЛЫЙ ЭКРАН: 1 колонка карточек + секции вертикально';
            }
            
            document.getElementById('layoutInfo').textContent = layoutInfo;
        }
        
        updateScreenInfo();
        window.addEventListener('resize', updateScreenInfo);
    </script>
</body>
</html>"""
    
    with open('dashboard_layout_debug.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("🔍 ОТЛАДОЧНЫЙ HTML СОЗДАН")
    print("=" * 50)
    print("📄 Файл: dashboard_layout_debug.html")
    print("🌐 Откройте файл в браузере для проверки layout")
    print()
    print("🎯 ЧТО ПРОВЕРЯТЬ:")
    print("- При ширине >900px: 4 карточки + горизонтальные секции")
    print("- При ширине ≤900px: 2×2 карточки + вертикальные секции")
    print("- При ширине ≤480px: 1 колонка карточек")
    print()
    print("💡 Измените размер окна браузера для проверки адаптивности")


if __name__ == "__main__":
    create_debug_html()