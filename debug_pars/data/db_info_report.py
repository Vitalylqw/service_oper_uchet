"""
Database Information Report Script

Получает статистическую информацию по таблицам read_deals и read_positions
и выводит в удобном формате.
"""

from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.models import ReadModelDeal, ReadModelPosition


class DBInfoReporter:
    """Генератор отчета о состоянии базы данных."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.config)
    
    async def get_read_deals_info(self, session: AsyncSession) -> dict:
        """Получает информацию по таблице read_deals."""
        
        # Количество строк
        total_count_query = select(func.count()).select_from(ReadModelDeal)
        total_count = await session.scalar(total_count_query)
        
        # Количество уникальных deal_key
        unique_deal_key_query = select(func.count(func.distinct(ReadModelDeal.deal_key)))
        unique_deal_key = await session.scalar(unique_deal_key_query)
        
        # Количество уникальных invoice_info
        unique_invoice_info_query = select(func.count(func.distinct(ReadModelDeal.invoice_info)))
        unique_invoice_info = await session.scalar(unique_invoice_info_query)
        
        # Количество уникальных period_full_name
        unique_period_query = select(func.count(func.distinct(ReadModelDeal.period_full_name)))
        unique_period = await session.scalar(unique_period_query)
        
        # Суммы по полям
        sums_query = select(
            func.sum(ReadModelDeal.items_count).label('total_items_count'),
            func.sum(ReadModelDeal.calc_revenue_amount).label('total_calc_revenue'),
            func.sum(ReadModelDeal.total_revenue_amount).label('total_revenue_amount')
        )
        sums_result = await session.execute(sums_query)
        sums = sums_result.first()
        
        return {
            "table": "read_deals",
            "total_rows": total_count or 0,
            "unique_deal_keys": unique_deal_key or 0,
            "unique_invoice_info": unique_invoice_info or 0,
            "unique_period_full_names": unique_period or 0,
            "sums": {
                "items_count": float(sums.total_items_count or 0),
                "calc_revenue_amount": float(sums.total_calc_revenue or 0),
                "total_revenue_amount": float(sums.total_revenue_amount or 0)
            }
        }
    
    async def get_read_positions_info(self, session: AsyncSession) -> dict:
        """Получает информацию по таблице read_positions."""
        
        # Количество строк
        total_count_query = select(func.count()).select_from(ReadModelPosition)
        total_count = await session.scalar(total_count_query)
        
        # Количество уникальных deal_key
        unique_deal_key_query = select(func.count(func.distinct(ReadModelPosition.deal_key)))
        unique_deal_key = await session.scalar(unique_deal_key_query)
        
        # Количество уникальных deal_id
        unique_deal_id_query = select(func.count(func.distinct(ReadModelPosition.deal_id)))
        unique_deal_id = await session.scalar(unique_deal_id_query)
        
        # Количество уникальных hash_key
        unique_hash_key_query = select(func.count(func.distinct(ReadModelPosition.hash_key)))
        unique_hash_key = await session.scalar(unique_hash_key_query)
        
        # Сумма по полю revenue_amount
        revenue_sum_query = select(func.sum(ReadModelPosition.revenue_amount))
        revenue_sum = await session.scalar(revenue_sum_query)
        
        return {
            "table": "read_positions",
            "total_rows": total_count or 0,
            "unique_deal_keys": unique_deal_key or 0,
            "unique_deal_ids": unique_deal_id or 0,
            "unique_hash_keys": unique_hash_key or 0,
            "sums": {
                "revenue_amount": float(revenue_sum or 0)
            }
        }
    
    async def generate_report(self) -> dict:
        """Генерирует полный отчет о базе данных."""
        
        try:
            async with self.db_manager.get_async_session() as session:
                # Получаем информацию по обеим таблицам
                deals_info = await self.get_read_deals_info(session)
                positions_info = await self.get_read_positions_info(session)
                
                report = {
                    "database_info_report": {
                        "timestamp": asyncio.get_event_loop().time(),
                        "read_deals": deals_info,
                        "read_positions": positions_info
                    }
                }
                
                return report
                
        except Exception as e:
            return {
                "error": f"Failed to generate report: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }
    
    def format_console_output(self, report: dict) -> str:
        """Форматирует отчет для вывода в консоль."""
        
        if "error" in report:
            return f"❌ ОШИБКА: {report['error']}"
        
        data = report["database_info_report"]
        deals = data["read_deals"]
        positions = data["read_positions"]
        
        output = []
        output.append("=" * 80)
        output.append("🗄️  ОТЧЕТ О СОСТОЯНИИ БАЗЫ ДАННЫХ")
        output.append("=" * 80)
        output.append("")
        
        # Информация по read_deals
        output.append("📊 ТАБЛИЦА: read_deals")
        output.append("-" * 40)
        output.append(f"Количество строк: {deals['total_rows']:,}")
        output.append(f"Уникальных deal_key: {deals['unique_deal_keys']:,}")
        output.append(f"Уникальных invoice_info: {deals['unique_invoice_info']:,}")
        output.append(f"Уникальных period_full_name: {deals['unique_period_full_names']:,}")
        output.append("")
        output.append("💰 СУММЫ:")
        output.append(f"  items_count: {deals['sums']['items_count']:,.0f}")
        output.append(f"  calc_revenue_amount: {deals['sums']['calc_revenue_amount']:,.2f}")
        output.append(f"  total_revenue_amount: {deals['sums']['total_revenue_amount']:,.2f}")
        output.append("")
        
        # Информация по read_positions
        output.append("📋 ТАБЛИЦА: read_positions")
        output.append("-" * 40)
        output.append(f"Количество строк: {positions['total_rows']:,}")
        output.append(f"Уникальных deal_key: {positions['unique_deal_keys']:,}")
        output.append(f"Уникальных deal_id: {positions['unique_deal_ids']:,}")
        output.append(f"Уникальных hash_key: {positions['unique_hash_keys']:,}")
        output.append("")
        output.append("💰 СУММЫ:")
        output.append(f"  revenue_amount: {positions['sums']['revenue_amount']:,.2f}")
        output.append("")
        
        output.append("=" * 80)
        
        return "\n".join(output)


async def main():
    """Основная функция для запуска отчета."""
    
    print("🔍 Генерация отчета о состоянии базы данных...")
    print("")
    
    reporter = DBInfoReporter()
    
    # Генерируем отчет
    report = await reporter.generate_report()
    
    # Выводим в консоль
    console_output = reporter.format_console_output(report)
    print(console_output)
    
    # Сохраняем JSON отчет
    output_file = Path(__file__).parent / "db_info_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"📄 JSON отчет сохранен: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())