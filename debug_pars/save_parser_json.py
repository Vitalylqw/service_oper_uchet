#!/usr/bin/env python3
"""
Скрипт для сохранения JSON данных после парсинга Excel файла.
Создает детальный JSON отчет со всеми сделками и позициями.
Обновлен для соответствия актуальной архитектуре проекта.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from application.excel_parser.parser import ExcelParserService
from application.excel_parser.models import ParseResult, ParseStats
from domain.models import Deal, DealItem, SyncSession, SyncType


async def save_parser_json():
    """Парсит Excel файл и сохраняет результат в JSON."""
    excel_file = Path("data/real_data_for_testing/Data_source_excel.xlsx")
    output_file = Path("debug_pars/parsed_data_detailed.json")
    
    print(f"📁 Парсинг файла: {excel_file}")
    
    if not excel_file.exists():
        print(f"❌ Файл не найден: {excel_file}")
        return
    
    # Создаем сессию для парсинга
    session = SyncSession(
        sync_type=SyncType.MANUAL,
        source_file_path=str(excel_file),
        created_by="json_saver"
    )
    
    # Парсим файл
    parser = ExcelParserService()
    result = await parser.parse_file(str(excel_file), session)
    
    print(f"✅ Парсинг завершен:")
    print(f"   📊 Сделок: {len(result.deals)}")
    print(f"   📦 Позиций: {sum(len(deal.items) for deal in result.deals)}")
    print(f"   📈 Статистика: {result.stats}")
    print(f"   📁 Файл: {result.file_path}")
    print(f"   📏 Размер: {result.file_size} байт")
    
    # Подготавливаем данные для JSON
    json_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_file": str(excel_file),
            "file_info": {
                "file_path": result.file_path,
                "file_size": result.file_size,
                "file_hash": result.file_hash,
                "parsed_at": result.parsed_at.isoformat()
            },
            "parser_stats": {
                "total_sheets": result.stats.total_sheets,
                "processed_sheets": result.stats.processed_sheets,
                "failed_sheets": result.stats.failed_sheets,
                "total_deals": result.stats.total_deals,
                "processed_deals": result.stats.processed_deals,
                "failed_deals": result.stats.failed_deals,
                "total_items": result.stats.total_items,
                "processed_items": result.stats.processed_items,
                "failed_items": result.stats.failed_items,
                "errors": result.stats.errors,
                "warnings": result.stats.warnings,
                "success_rates": {
                    "sheets": result.stats.success_rate_sheets,
                    "deals": result.stats.success_rate_deals,
                    "items": result.stats.success_rate_items
                }
            }
        },
        "deals": [],
        "all_items": []
    }
    
    # Добавляем сделки
    for deal in result.deals:
        deal_data = {
            "id": str(deal.id),
            "client_name": deal.client_name,
            "invoice_number": deal.invoice_number,
            "invoice_info": deal.invoice_info,
            "invoice_date": deal.invoice_date,
            "upd_number": deal.upd_number,
            "seller": deal.seller,
            "period": str(deal.period),
            "is_shipped": deal.is_shipped.value if deal.is_shipped else None,
            "is_paid": deal.is_paid.value if deal.is_paid else None,
            "total_revenue": float(deal.total_revenue.amount) if deal.total_revenue else 0,
            "total_margin": float(deal.total_margin.amount) if deal.total_margin else 0,
            "total_cost": float(deal.total_cost.amount) if deal.total_cost else 0,
            "kickback_amount": float(deal.kickback_amount.amount) if deal.kickback_amount else 0,
            "deal_key": deal.deal_key,
            "hash_key": str(deal.hash_key),
            "created_at": deal.created_at.isoformat(),
            "updated_at": deal.updated_at.isoformat() if deal.updated_at else None,
            "items_count": len(deal.items),
            "items": []
        }
        
        # Добавляем позиции сделки
        for item in deal.items:
            item_data = {
                "id": str(item.id),
                "deal_id": str(item.deal_id) if item.deal_id else None,
                "product_name": item.product_name,
                "supplier_name": item.supplier_name,
                "quantity": str(item.quantity) if item.quantity else "0",
                "purchase_price": float(item.purchase_price.amount) if item.purchase_price else 0,
                "sale_price": float(item.sale_price.amount) if item.sale_price else 0,
                "revenue": float(item.revenue.amount) if item.revenue else 0,
                "margin": float(item.margin.amount) if item.margin else 0,
                "cost": float(item.cost.amount) if item.cost else 0,
                "pickup_date": item.pickup_date,
                "position_number": item.position_number,
                "item_key": item.item_key,
                "hash_key": str(item.hash_key),
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
            
            deal_data["items"].append(item_data)
            json_data["all_items"].append(item_data)
        
        json_data["deals"].append(deal_data)
    
    # Сохраняем JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 JSON сохранен: {output_file}")
    print(f"   📁 Размер файла: {output_file.stat().st_size / 1024:.1f} KB")
    
    # Создаем краткую сводку
    summary_file = Path("debug_pars/parser_summary.json")
    summary_data = {
        "timestamp": datetime.now().isoformat(),
        "source_file": str(excel_file),
        "totals": {
            "deals_count": len(result.deals),
            "items_count": len(json_data["all_items"]),
            "total_revenue": sum(deal["total_revenue"] for deal in json_data["deals"]),
            "total_margin": sum(deal["total_margin"] for deal in json_data["deals"])
        },
        "parser_stats": json_data["metadata"]["parser_stats"],
        "sample_deals": json_data["deals"][:3] if json_data["deals"] else []
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    print(f"📋 Краткая сводка: {summary_file}")
    
    # Проверяем потенциальные проблемы
    print("\n🔍 Анализ потенциальных проблем:")
    
    empty_product_items = [item for item in json_data["all_items"] if not item["product_name"].strip()]
    if empty_product_items:
        print(f"   ⚠️  Найдено {len(empty_product_items)} позиций с пустыми названиями")
        for item in empty_product_items[:5]:
            print(f"      - ID: {item['id']}, Deal: {item['deal_id']}")
    else:
        print("   ✅ Все позиции имеют названия товаров")
    
    zero_revenue_items = [item for item in json_data["all_items"] if item["revenue"] == 0]
    if zero_revenue_items:
        print(f"   ⚠️  Найдено {len(zero_revenue_items)} позиций с нулевой выручкой")
    
    print(f"\n📊 Статистика парсера vs. фактические данные:")
    print(f"   Парсер считает сделок: {result.stats.total_deals}")
    print(f"   Фактически в JSON: {len(json_data['deals'])}")
    print(f"   Парсер считает позиций: {result.stats.total_items}")
    print(f"   Фактически в JSON: {len(json_data['all_items'])}")
    
    if result.stats.total_deals != len(json_data['deals']):
        print(f"   ⚠️  РАСХОЖДЕНИЕ СДЕЛОК: {result.stats.total_deals - len(json_data['deals'])}")
    else:
        print(f"   ✅ Количество сделок совпадает")
        
    if result.stats.total_items != len(json_data['all_items']):
        print(f"   ⚠️  РАСХОЖДЕНИЕ ПОЗИЦИЙ: {result.stats.total_items - len(json_data['all_items'])}")
    else:
        print(f"   ✅ Количество позиций совпадает")
    
    # Показываем статистику успешности
    print(f"\n📈 Показатели успешности:")
    print(f"   📊 Листы: {result.stats.success_rate_sheets:.1f}%")
    print(f"   🤝 Сделки: {result.stats.success_rate_deals:.1f}%")
    print(f"   📦 Позиции: {result.stats.success_rate_items:.1f}%")
    
    if result.stats.errors:
        print(f"\n❌ Ошибки ({len(result.stats.errors)}):")
        for i, error in enumerate(result.stats.errors[:5], 1):
            print(f"   {i}. {error}")
        if len(result.stats.errors) > 5:
            print(f"   ... и еще {len(result.stats.errors) - 5} ошибок")
            
    if result.stats.warnings:
        print(f"\n⚠️ Предупреждения ({len(result.stats.warnings)}):")
        for i, warning in enumerate(result.stats.warnings[:3], 1):
            print(f"   {i}. {warning}")
        if len(result.stats.warnings) > 3:
            print(f"   ... и еще {len(result.stats.warnings) - 3} предупреждений")


if __name__ == "__main__":
    asyncio.run(save_parser_json())