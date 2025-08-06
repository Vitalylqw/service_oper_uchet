"""
Duplication Analysis Script

Анализирует причины троекратного дублирования записей в таблице read_positions.
Исследует различия между дублированными записями.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.models import ReadModelPosition


class DuplicationAnalyzer:
    """Анализатор дублирования записей."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.config)
    
    async def analyze_duplicate_differences(self, session: AsyncSession) -> dict:
        """Анализирует различия между дублированными записями."""
        
        # Берем несколько примеров для детального анализа
        sample_hashes_query = select(
            ReadModelPosition.hash_key
        ).group_by(
            ReadModelPosition.hash_key
        ).limit(5)
        
        result = await session.execute(sample_hashes_query)
        sample_hashes = [row[0] for row in result.fetchall()]
        
        analysis_results = []
        
        for hash_key in sample_hashes:
            # Получаем все записи с этим hash_key
            positions_query = select(
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
                ReadModelPosition.is_active,
                ReadModelPosition.created_at,
                ReadModelPosition.updated_at,
                ReadModelPosition.version
            ).where(
                ReadModelPosition.hash_key == hash_key
            ).order_by(
                ReadModelPosition.created_at
            )
            
            positions_result = await session.execute(positions_query)
            positions = positions_result.fetchall()
            
            # Анализируем различия
            position_data = []
            for pos in positions:
                position_data.append({
                    'id': str(pos.id),
                    'deal_id': str(pos.deal_id),
                    'deal_key': pos.deal_key,
                    'position_number': pos.position_number,
                    'hash_key': pos.hash_key,
                    'product_name': pos.product_name,
                    'supplier_name': pos.supplier_name,
                    'pickup_date': pos.pickup_date,
                    'quantity': float(pos.quantity) if pos.quantity else None,
                    'purchase_price_amount': float(pos.purchase_price_amount) if pos.purchase_price_amount else None,
                    'sale_price_amount': float(pos.sale_price_amount) if pos.sale_price_amount else None,
                    'revenue_amount': float(pos.revenue_amount) if pos.revenue_amount else None,
                    'margin_amount': float(pos.margin_amount) if pos.margin_amount else None,
                    'cost_amount': float(pos.cost_amount) if pos.cost_amount else None,
                    'client_name': pos.client_name,
                    'period_month': pos.period_month,
                    'period_year': pos.period_year,
                    'is_active': pos.is_active,
                    'created_at': pos.created_at.isoformat() if pos.created_at else None,
                    'updated_at': pos.updated_at.isoformat() if pos.updated_at else None,
                    'version': pos.version
                })
            
            # Находим различия между записями
            differences = self.find_differences(position_data)
            
            analysis_results.append({
                'hash_key': hash_key,
                'count': len(positions),
                'positions': position_data,
                'differences': differences
            })
        
        return analysis_results
    
    def find_differences(self, positions: list[dict]) -> dict:
        """Находит различия между позициями с одинаковым hash_key."""
        
        if len(positions) <= 1:
            return {"type": "no_duplicates"}
        
        differences = {
            "identical_fields": [],
            "different_fields": {},
            "analysis": {
                "completely_identical": True,
                "differs_only_in_system_fields": True,
                "differs_in_business_fields": False
            }
        }
        
        # Поля, которые мы считаем системными (могут отличаться при дублировании)
        system_fields = {'id', 'created_at', 'updated_at', 'version'}
        
        # Поля, которые мы считаем бизнес-логическими (не должны отличаться)
        business_fields = {
            'deal_id', 'deal_key', 'position_number', 'hash_key', 'product_name',
            'supplier_name', 'pickup_date', 'quantity', 'purchase_price_amount',
            'sale_price_amount', 'revenue_amount', 'margin_amount', 'cost_amount',
            'client_name', 'period_month', 'period_year', 'is_active'
        }
        
        first_position = positions[0]
        
        for field in first_position.keys():
            values = [pos.get(field) for pos in positions]
            unique_values = list(set(str(v) for v in values if v is not None))
            
            if len(unique_values) <= 1:
                differences["identical_fields"].append(field)
            else:
                differences["different_fields"][field] = values
                differences["analysis"]["completely_identical"] = False
                
                if field in business_fields:
                    differences["analysis"]["differs_in_business_fields"] = True
                    differences["analysis"]["differs_only_in_system_fields"] = False
        
        return differences
    
    async def get_duplication_statistics(self, session: AsyncSession) -> dict:
        """Получает общую статистику дублирования."""
        
        # Общее количество записей
        total_query = select(func.count()).select_from(ReadModelPosition)
        total_count = await session.scalar(total_query)
        
        # Количество уникальных hash_key
        unique_query = select(func.count(func.distinct(ReadModelPosition.hash_key)))
        unique_count = await session.scalar(unique_query)
        
        # Распределение по версиям
        version_query = select(
            ReadModelPosition.version,
            func.count(ReadModelPosition.version).label('count')
        ).group_by(
            ReadModelPosition.version
        ).order_by(
            ReadModelPosition.version
        )
        
        version_result = await session.execute(version_query)
        version_distribution = {str(row.version): row.count for row in version_result.fetchall()}
        
        # Распределение по is_active
        active_query = select(
            ReadModelPosition.is_active,
            func.count(ReadModelPosition.is_active).label('count')
        ).group_by(
            ReadModelPosition.is_active
        )
        
        active_result = await session.execute(active_query)
        active_distribution = {str(row.is_active): row.count for row in active_result.fetchall()}
        
        return {
            "total_records": total_count,
            "unique_hash_keys": unique_count,
            "duplication_factor": total_count / unique_count if unique_count > 0 else 0,
            "version_distribution": version_distribution,
            "active_distribution": active_distribution
        }
    
    async def generate_analysis(self) -> dict:
        """Генерирует полный анализ дублирования."""
        
        try:
            async with self.db_manager.get_async_session() as session:
                # Получаем общую статистику
                statistics = await self.get_duplication_statistics(session)
                
                # Анализируем различия в дубликатах
                duplicate_analysis = await self.analyze_duplicate_differences(session)
                
                analysis = {
                    "duplication_analysis": {
                        "timestamp": asyncio.get_event_loop().time(),
                        "statistics": statistics,
                        "sample_analysis": duplicate_analysis
                    }
                }
                
                return analysis
                
        except Exception as e:
            return {
                "error": f"Failed to generate duplication analysis: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }
    
    def format_console_output(self, analysis: dict) -> str:
        """Форматирует анализ для вывода в консоль."""
        
        if "error" in analysis:
            return f"❌ ОШИБКА: {analysis['error']}"
        
        data = analysis["duplication_analysis"]
        stats = data["statistics"]
        samples = data["sample_analysis"]
        
        output = []
        output.append("=" * 80)
        output.append("🔍 АНАЛИЗ ДУБЛИРОВАНИЯ ЗАПИСЕЙ")
        output.append("=" * 80)
        output.append("")
        
        # Общая статистика
        output.append("📊 ОБЩАЯ СТАТИСТИКА ДУБЛИРОВАНИЯ:")
        output.append("-" * 40)
        output.append(f"Всего записей: {stats['total_records']:,}")
        output.append(f"Уникальных hash_key: {stats['unique_hash_keys']:,}")
        output.append(f"Коэффициент дублирования: {stats['duplication_factor']:.1f}x")
        output.append("")
        
        # Распределение по версиям
        output.append("📋 РАСПРЕДЕЛЕНИЕ ПО ВЕРСИЯМ:")
        output.append("-" * 40)
        for version, count in stats['version_distribution'].items():
            output.append(f"  Версия {version}: {count:,} записей")
        output.append("")
        
        # Распределение по активности
        output.append("🔄 РАСПРЕДЕЛЕНИЕ ПО АКТИВНОСТИ:")
        output.append("-" * 40)
        for active, count in stats['active_distribution'].items():
            output.append(f"  is_active = {active}: {count:,} записей")
        output.append("")
        
        # Анализ различий в примерах
        output.append("🔍 АНАЛИЗ РАЗЛИЧИЙ В ДУБЛИКАТАХ:")
        output.append("-" * 40)
        
        for i, sample in enumerate(samples[:3], 1):  # Показываем первые 3 примера
            output.append(f"\n🔸 ПРИМЕР {i}: Hash {sample['hash_key'][:16]}...")
            
            differences = sample['differences']
            analysis_result = differences['analysis']
            
            if analysis_result['completely_identical']:
                output.append("  ✅ Записи полностью идентичны (кроме системных полей)")
            elif analysis_result['differs_only_in_system_fields']:
                output.append("  ⚠️  Различия только в системных полях")
            else:
                output.append("  ❌ Различия в бизнес-полях!")
            
            if differences['different_fields']:
                output.append("  Различающиеся поля:")
                for field, values in differences['different_fields'].items():
                    if len(str(values)) < 100:  # Показываем только короткие значения
                        output.append(f"    {field}: {values}")
                    else:
                        output.append(f"    {field}: [значения слишком длинные]")
        
        output.append("")
        output.append("=" * 80)
        
        return "\n".join(output)


async def main():
    """Основная функция для запуска анализа дублирования."""
    
    print("🔍 Запуск анализа дублирования записей...")
    print("")
    
    analyzer = DuplicationAnalyzer()
    
    # Генерируем анализ
    analysis = await analyzer.generate_analysis()
    
    # Выводим в консоль
    console_output = analyzer.format_console_output(analysis)
    print(console_output)
    
    # Сохраняем JSON отчет
    output_file = Path(__file__).parent / "duplication_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"📄 JSON анализ сохранен: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())