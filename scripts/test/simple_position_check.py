"""
Simple script to check position_number distribution in the database.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.models import ReadModelPosition
from sqlalchemy import func


async def main():
    """Check position_number distribution."""
    print("🔍 Проверяем распределение position_number в базе данных...")
    
    # Создаем менеджер базы данных
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    async with db_manager.get_async_session() as session:
        # Получаем распределение position_number
        from sqlalchemy import select
        
        query = select(
            ReadModelPosition.position_number,
            func.count(ReadModelPosition.id).label('count')
        ).group_by(ReadModelPosition.position_number).order_by(ReadModelPosition.position_number)
        
        result = await session.execute(query)
        position_counts = result.all()
        
        total = sum(count for pos_num, count in position_counts)
        
        print(f'📊 Всего записей: {total}')
        print(f'📊 Уникальных значений position_number: {len(position_counts)}')
        print()
        
        # Показываем первые 15 значений
        print("📊 Первые значения:")
        for i, (pos_num, count) in enumerate(position_counts[:15]):
            percent = (count / total) * 100 if total > 0 else 0
            print(f'  {pos_num:3d}: {count:4d} записей ({percent:5.1f}%)')
        
        if len(position_counts) > 15:
            print(f'  ... и еще {len(position_counts) - 15} значений')
            
        # Показываем последние 5 значений если их много
        if len(position_counts) > 15:
            print()
            print('📊 Последние значения:')
            for pos_num, count in position_counts[-5:]:
                percent = (count / total) * 100 if total > 0 else 0
                print(f'  {pos_num:3d}: {count:4d} записей ({percent:5.1f}%)')
        
        # Статистика по единицам
        ones_count = next((count for pos_num, count in position_counts if pos_num == 1), 0)
        ones_percent = (ones_count / total) * 100 if total > 0 else 0
        
        print()
        print(f"📈 Статистика:")
        print(f"   Записей с position_number = 1: {ones_count} ({ones_percent:.1f}%)")
        print(f"   Минимальный position_number: {position_counts[0][0] if position_counts else 'N/A'}")
        print(f"   Максимальный position_number: {position_counts[-1][0] if position_counts else 'N/A'}")


if __name__ == "__main__":
    asyncio.run(main())