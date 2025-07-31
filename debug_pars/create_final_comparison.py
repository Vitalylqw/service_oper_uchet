import json
import sqlite3
from pathlib import Path
from typing import Any, Dict
from datetime import datetime


def get_db_data() -> Dict[str, Any]:
    """Получает данные из БД"""
    db_path = Path(__file__).parent.parent / "data" / "service_oper_uchet.sqlite"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Основная статистика
    cursor.execute("SELECT COUNT(*) FROM read_deals")
    deals_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_revenue_amount) FROM read_deals")
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(total_margin_amount) FROM read_deals")
    total_margin = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(items_count) FROM read_deals")
    total_items = cursor.fetchone()[0] or 0
    
    # Статистика по позициям
    cursor.execute("SELECT COUNT(*) FROM read_positions")
    positions_count = cursor.fetchone()[0]
    
    # Сессии
    cursor.execute("SELECT COUNT(*) FROM sync_sessions")
    sessions_count = cursor.fetchone()[0]
    
    # События
    cursor.execute("SELECT COUNT(*) FROM event_store")
    events_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_deals": deals_count,
        "total_items": total_items,
        "total_positions": positions_count,
        "total_revenue": float(total_revenue),
        "total_margin": float(total_margin),
        "average_revenue_per_deal": float(total_revenue / deals_count) if deals_count > 0 else 0,
        "average_margin_per_deal": float(total_margin / deals_count) if deals_count > 0 else 0,
        "margin_percentage": float(total_margin / total_revenue * 100) if total_revenue > 0 else 0,
        "sessions_count": sessions_count,
        "events_count": events_count
    }


def get_parser_data() -> Dict[str, Any]:
    """Получает данные из отчета парсера"""
    parser_file = Path(__file__).parent / "parser_report.json"
    
    with open(parser_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return {
        "total_deals": data["summary"]["total_deals"],
        "total_items": data["summary"]["total_items"],
        "total_revenue": data["summary"]["total_revenue"],
        "total_margin": data["summary"]["total_margin"],
        "average_revenue_per_deal": data["summary"]["average_revenue_per_deal"],
        "average_margin_per_deal": data["summary"]["average_margin_per_deal"],
        "margin_percentage": data["financial_metrics"]["margin_percentage"]
    }


def format_number(value: Any) -> str:
    """Форматирует число для отображения"""
    if isinstance(value, (int, float)):
        if isinstance(value, int):
            return f"{value:,}"
        else:
            return f"{value:,.2f}"
    return str(value)


def create_comparison_table() -> str:
    """Создает таблицу сравнения"""
    parser_data = get_parser_data()
    db_data = get_db_data()
    
    table = []
    table.append("=" * 100)
    table.append("СРАВНЕНИЕ ДАННЫХ: ПАРСЕР vs БАЗА ДАННЫХ")
    table.append("=" * 100)
    table.append(f"{'Метрика':<40} {'Парсер':<20} {'БД':<20} {'Разница':<15}")
    table.append("-" * 100)
    
    # Основные метрики
    metrics = [
        ("Общее количество сделок", "total_deals"),
        ("Общее количество позиций", "total_items"),
        ("Общая выручка", "total_revenue"),
        ("Общая маржа", "total_margin"),
        ("Средняя выручка на сделку", "average_revenue_per_deal"),
        ("Средняя маржа на сделку", "average_margin_per_deal"),
        ("Процент маржи", "margin_percentage"),
    ]
    
    for metric_name, metric_key in metrics:
        parser_value = parser_data.get(metric_key, 0)
        db_value = db_data.get(metric_key, 0)
        
        if isinstance(parser_value, (int, float)) and isinstance(db_value, (int, float)):
            difference = parser_value - db_value
            difference_str = format_number(difference)
        else:
            difference_str = "N/A"
        
        parser_str = format_number(parser_value)
        db_str = format_number(db_value)
        
        table.append(f"{metric_name:<40} {parser_str:<20} {db_str:<20} {difference_str:<15}")
    
    # Дополнительная информация о БД
    table.append("-" * 100)
    table.append("ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ О БД:")
    table.append(f"Количество позиций товаров: {db_data.get('total_positions', 0):,}")
    table.append(f"Количество сессий синхронизации: {db_data.get('sessions_count', 0):,}")
    table.append(f"Количество событий: {db_data.get('events_count', 0):,}")
    
    # Анализ расхождений
    table.append("-" * 100)
    table.append("АНАЛИЗ РАСХОЖДЕНИЙ:")
    
    deals_diff = parser_data.get('total_deals', 0) - db_data.get('total_deals', 0)
    if deals_diff != 0:
        table.append(f"⚠️  Сделок в парсере больше на {deals_diff} (возможно, фильтрация в БД)")
    
    revenue_diff = parser_data.get('total_revenue', 0) - db_data.get('total_revenue', 0)
    if revenue_diff != 0:
        table.append(f"⚠️  Выручка в парсере больше на {revenue_diff:,.2f}")
    
    margin_diff = parser_data.get('total_margin', 0) - db_data.get('total_margin', 0)
    if margin_diff != 0:
        table.append(f"⚠️  Маржа в парсере больше на {margin_diff:,.2f}")
    
    if deals_diff == 0 and revenue_diff == 0 and margin_diff == 0:
        table.append("✅ Данные парсера и БД полностью совпадают")
    
    table.append("=" * 100)
    
    return "\n".join(table)


def main():
    """Основная функция"""
    print("Создание финальной таблицы сравнения...")
    
    comparison_table = create_comparison_table()
    
    # Сохраняем в файл
    output_file = Path(__file__).parent / "final_comparison_table.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(comparison_table)
    
    print(f"Таблица сохранена: {output_file}")
    print("\n" + comparison_table)


if __name__ == "__main__":
    main() 