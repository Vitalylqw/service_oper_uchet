"""
Hash Key Distribution Analysis Script

Анализирует распределение hash_key в таблице read_positions и находит примеры
хешей с разным количеством вхождений в базе данных.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.models import ReadModelPosition


class HashKeyDistributionAnalyzer:
    """Анализатор распределения hash_key в базе данных."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.config)
    
    async def get_hash_key_distribution(self, session: AsyncSession) -> dict:
        """Получает распределение hash_key по количеству вхождений."""
        
        # Запрос для подсчета количества вхождений каждого hash_key
        distribution_query = select(
            ReadModelPosition.hash_key,
            func.count(ReadModelPosition.hash_key).label('count')
        ).group_by(
            ReadModelPosition.hash_key
        ).order_by(
            func.count(ReadModelPosition.hash_key).desc()
        )
        
        result = await session.execute(distribution_query)
        hash_counts = result.fetchall()
        
        # Группируем по количеству вхождений
        count_distribution = defaultdict(list)
        for hash_key, count in hash_counts:
            count_distribution[count].append(hash_key)
        
        # Создаем статистику распределения
        distribution_stats = {}
        for count, hash_list in count_distribution.items():
            distribution_stats[count] = {
                'count_occurrences': count,
                'number_of_hashes': len(hash_list),
                'examples': hash_list[:5]  # Берем первые 5 примеров
            }
        
        return {
            'total_unique_hashes': len(hash_counts),
            'distribution_by_count': dict(sorted(distribution_stats.items(), reverse=True)),
            'raw_data': [(hash_key, count) for hash_key, count in hash_counts[:20]]  # Топ 20
        }
    
    async def get_detailed_examples(self, session: AsyncSession, target_counts: list[int]) -> dict:
        """Получает детальные примеры для указанных количеств вхождений."""
        
        examples = {}
        
        for target_count in target_counts:
            # Находим hash_key с указанным количеством вхождений
            count_query = select(
                ReadModelPosition.hash_key,
                func.count(ReadModelPosition.hash_key).label('count')
            ).group_by(
                ReadModelPosition.hash_key
            ).having(
                func.count(ReadModelPosition.hash_key) == target_count
            ).limit(3)  # Берем 3 примера
            
            result = await session.execute(count_query)
            hash_examples = result.fetchall()
            
            if hash_examples:
                examples[target_count] = []
                
                for hash_key, count in hash_examples:
                    # Получаем детальную информацию о позициях с этим hash_key
                    details_query = select(
                        ReadModelPosition.id,
                        ReadModelPosition.deal_id,
                        ReadModelPosition.deal_key,
                        ReadModelPosition.position_number,
                        ReadModelPosition.product_name,
                        ReadModelPosition.client_name,
                        ReadModelPosition.revenue_amount,
                        ReadModelPosition.created_at,
                        ReadModelPosition.updated_at
                    ).where(
                        ReadModelPosition.hash_key == hash_key
                    ).order_by(
                        ReadModelPosition.created_at
                    )
                    
                    details_result = await session.execute(details_query)
                    positions = details_result.fetchall()
                    
                    example_data = {
                        'hash_key': hash_key,
                        'count': count,
                        'positions': []
                    }
                    
                    for pos in positions:
                        example_data['positions'].append({
                            'id': str(pos.id),
                            'deal_id': str(pos.deal_id),
                            'deal_key': pos.deal_key,
                            'position_number': pos.position_number,
                            'product_name': pos.product_name[:100] + '...' if len(pos.product_name) > 100 else pos.product_name,
                            'client_name': pos.client_name,
                            'revenue_amount': float(pos.revenue_amount) if pos.revenue_amount else 0,
                            'created_at': pos.created_at.isoformat() if pos.created_at else None,
                            'updated_at': pos.updated_at.isoformat() if pos.updated_at else None
                        })
                    
                    examples[target_count].append(example_data)
        
        return examples
    
    async def generate_analysis(self) -> dict:
        """Генерирует полный анализ распределения hash_key."""
        
        try:
            async with self.db_manager.get_async_session() as session:
                # Получаем общее распределение
                distribution = await self.get_hash_key_distribution(session)
                
                # Определяем интересные случаи для детального анализа
                available_counts = list(distribution['distribution_by_count'].keys())
                target_counts = []
                
                # Добавляем наиболее частые случаи
                if available_counts:
                    target_counts.append(max(available_counts))  # Максимальное количество
                
                # Добавляем случаи с несколькими вхождениями
                for count in [5, 4, 3, 2]:
                    if count in available_counts:
                        target_counts.append(count)
                        break  # Берем первый найденный
                
                # Добавляем уникальные (1 вхождение)
                if 1 in available_counts:
                    target_counts.append(1)
                
                # Получаем детальные примеры
                detailed_examples = await self.get_detailed_examples(session, target_counts)
                
                analysis = {
                    "hash_key_distribution_analysis": {
                        "timestamp": asyncio.get_event_loop().time(),
                        "summary": {
                            "total_unique_hashes": distribution['total_unique_hashes'],
                            "distribution_categories": len(distribution['distribution_by_count']),
                            "analyzed_counts": target_counts
                        },
                        "distribution": distribution,
                        "detailed_examples": detailed_examples
                    }
                }
                
                return analysis
                
        except Exception as e:
            return {
                "error": f"Failed to generate analysis: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }
    
    def format_console_output(self, analysis: dict) -> str:
        """Форматирует анализ для вывода в консоль."""
        
        if "error" in analysis:
            return f"❌ ОШИБКА: {analysis['error']}"
        
        data = analysis["hash_key_distribution_analysis"]
        distribution = data["distribution"]["distribution_by_count"]
        examples = data["detailed_examples"]
        
        output = []
        output.append("=" * 80)
        output.append("🔍 АНАЛИЗ РАСПРЕДЕЛЕНИЯ HASH_KEY")
        output.append("=" * 80)
        output.append("")
        
        # Общая статистика
        output.append("📊 ОБЩАЯ СТАТИСТИКА:")
        output.append("-" * 40)
        output.append(f"Всего уникальных hash_key: {data['summary']['total_unique_hashes']:,}")
        output.append(f"Категорий по количеству: {data['summary']['distribution_categories']}")
        output.append("")
        
        # Распределение по количеству вхождений
        output.append("📈 РАСПРЕДЕЛЕНИЕ ПО КОЛИЧЕСТВУ ВХОЖДЕНИЙ:")
        output.append("-" * 40)
        for count, info in sorted(distribution.items(), reverse=True)[:10]:  # Топ 10
            output.append(f"  {count} вхождений: {info['number_of_hashes']:,} хешей")
        output.append("")
        
        # Топ хеши по количеству вхождений
        top_hashes = data["distribution"]["raw_data"][:10]
        if top_hashes:
            output.append("🔝 ТОП ХЕШИ ПО КОЛИЧЕСТВУ ВХОЖДЕНИЙ:")
            output.append("-" * 40)
            for hash_key, count in top_hashes:
                output.append(f"  {hash_key}: {count} раз")
        output.append("")
        
        # Детальные примеры
        output.append("🔍 ДЕТАЛЬНЫЕ ПРИМЕРЫ:")
        output.append("-" * 40)
        
        for count in sorted(examples.keys(), reverse=True):
            output.append(f"\n📋 ПРИМЕРЫ С {count} ВХОЖДЕНИЕМ(И):")
            output.append("-" * 30)
            
            for example in examples[count][:2]:  # Показываем максимум 2 примера на категорию
                output.append(f"  Hash: {example['hash_key']}")
                output.append(f"  Позиций: {len(example['positions'])}")
                
                for i, pos in enumerate(example['positions']):
                    output.append(f"    {i+1}. Deal: {pos['deal_key']}")
                    output.append(f"       Продукт: {pos['product_name']}")
                    output.append(f"       Клиент: {pos['client_name']}")
                    output.append(f"       Выручка: {pos['revenue_amount']:,.2f}")
                
                if len(examples[count]) > 1:
                    output.append("")
        
        output.append("")
        output.append("=" * 80)
        
        return "\n".join(output)


async def main():
    """Основная функция для запуска анализа."""
    
    print("🔍 Запуск анализа распределения hash_key...")
    print("")
    
    analyzer = HashKeyDistributionAnalyzer()
    
    # Генерируем анализ
    analysis = await analyzer.generate_analysis()
    
    # Выводим в консоль
    console_output = analyzer.format_console_output(analysis)
    print(console_output)
    
    # Сохраняем JSON отчет
    output_file = Path(__file__).parent / "hash_key_distribution_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"📄 JSON анализ сохранен: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())