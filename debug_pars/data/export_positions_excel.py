"""
Export Positions to Excel Script

Экспортирует все записи из таблицы read_positions в Excel файл
с форматированием и фильтрами.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.models import ReadModelPosition


class PositionsExcelExporter:
    """Экспортер позиций в Excel."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.config)
    
    async def export_all_positions(self) -> None:
        """Экспортирует все позиции в Excel файл."""
        
        try:
            async with self.db_manager.get_async_session() as session:
                print("🔍 Загрузка данных из базы...")
                
                # Получаем все записи
                query = select(
                    ReadModelPosition.id,
                    ReadModelPosition.deal_id,
                    ReadModelPosition.deal_key,
                    ReadModelPosition.position_number,
                    ReadModelPosition.hash_key,
                    ReadModelPosition.product_name,
                    ReadModelPosition.supplier_name,
                    ReadModelPosition.pickup_date,
                    ReadModelPosition.quantity,
                    ReadModelPosition.purchase_price_amount,
                    ReadModelPosition.sale_price_amount,
                    ReadModelPosition.revenue_amount,
                    ReadModelPosition.margin_amount,
                    ReadModelPosition.cost_amount,
                    ReadModelPosition.client_name,
                    ReadModelPosition.period_month,
                    ReadModelPosition.period_year,
                    ReadModelPosition.created_at,
                    ReadModelPosition.updated_at
                ).order_by(ReadModelPosition.created_at.desc())
                
                result = await session.execute(query)
                positions = result.fetchall()
                
                print(f"📊 Загружено {len(positions):,} записей")
                
                # Конвертируем в DataFrame
                print("🔄 Преобразование данных...")
                
                data = []
                for pos in positions:
                    data.append({
                        'ID': str(pos.id),
                        'Deal ID': str(pos.deal_id),
                        'Deal Key': pos.deal_key,
                        'Position Number': pos.position_number,
                        'Hash Key': pos.hash_key,
                        'Product Name': pos.product_name,
                        'Supplier Name': pos.supplier_name,
                        'Pickup Date': pos.pickup_date,
                        'Quantity': float(pos.quantity) if pos.quantity else None,
                        'Purchase Price': float(pos.purchase_price_amount) if pos.purchase_price_amount else None,
                        'Sale Price': float(pos.sale_price_amount) if pos.sale_price_amount else None,
                        'Revenue': float(pos.revenue_amount) if pos.revenue_amount else None,
                        'Margin': float(pos.margin_amount) if pos.margin_amount else None,
                        'Cost': float(pos.cost_amount) if pos.cost_amount else None,
                        'Client Name': pos.client_name,
                        'Period Month': pos.period_month,
                        'Period Year': pos.period_year,
                        'Created At': pos.created_at,
                        'Updated At': pos.updated_at
                    })
                
                df = pd.DataFrame(data)
                
                # Создаем Excel файл
                output_file = Path(__file__).parent / "positions_export.xlsx"
                
                print("📝 Создание Excel файла...")
                
                with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                    # Основной лист с данными
                    df.to_excel(writer, sheet_name='Positions', index=False)
                    
                    # Лист со статистикой
                    stats_data = {
                        'Metric': [
                            'Total Records',
                            'Unique Hash Keys',
                            'Unique Deal Keys',
                            'Unique Clients',
                            'Total Revenue',
                            'Total Margin',
                            'Total Cost',
                            'Average Revenue per Position'
                        ],
                        'Value': [
                            len(df),
                            df['Hash Key'].nunique(),
                            df['Deal Key'].nunique(),
                            df['Client Name'].nunique(),
                            df['Revenue'].sum(),
                            df['Margin'].sum(),
                            df['Cost'].sum(),
                            df['Revenue'].mean()
                        ]
                    }
                    
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                    
                    # Лист с анализом дублирования
                    duplication_analysis = df.groupby('Hash Key').agg({
                        'ID': 'count',
                        'Deal Key': lambda x: ', '.join(x.unique()[:3]),  # Первые 3 уникальных
                        'Client Name': 'first',
                        'Product Name': 'first',
                        'Revenue': 'first'
                    }).reset_index()
                    
                    duplication_analysis.columns = [
                        'Hash Key', 'Duplicate Count', 'Deal Keys', 
                        'Client', 'Product', 'Revenue'
                    ]
                    
                    duplication_analysis = duplication_analysis.sort_values(
                        'Duplicate Count', ascending=False
                    )
                    
                    duplication_analysis.to_excel(
                        writer, sheet_name='Duplication Analysis', index=False
                    )
                
                print(f"✅ Excel файл создан: {output_file}")
                print(f"📊 Экспортировано: {len(positions):,} записей")
                print(f"📋 Листы: Positions, Statistics, Duplication Analysis")
                
        except Exception as e:
            print(f"❌ Ошибка при экспорте: {e}")


async def main():
    """Основная функция."""
    
    print("📊 Экспорт позиций в Excel...")
    print("=" * 50)
    
    exporter = PositionsExcelExporter()
    await exporter.export_all_positions()


if __name__ == "__main__":
    # Проверяем наличие pandas
    try:
        import pandas as pd
        import openpyxl
    except ImportError:
        print("❌ Требуется установка pandas и openpyxl:")
        print("pip install pandas openpyxl")
        sys.exit(1)
    
    asyncio.run(main())