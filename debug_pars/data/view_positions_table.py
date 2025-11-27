"""
View Positions Table Script

Позволяет просматривать все строки из таблицы read_positions с различными
опциями фильтрации, сортировки и экспорта.
"""

from __future__ import annotations

import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select, text, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.models import ReadModelPosition


class PositionsTableViewer:
    """Просмотрщик таблицы read_positions."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.config)
    
    async def get_all_positions(
        self,
        session: AsyncSession,
        limit: Optional[int] = None,
        offset: int = 0,
        hash_key_filter: Optional[str] = None,
        deal_key_filter: Optional[str] = None,
        client_filter: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> tuple[list[dict], int]:
        """
        Получает позиции из таблицы с опциональными фильтрами.
        
        Args:
            session: Сессия БД
            limit: Лимит записей (None = все)
            offset: Смещение для пагинации
            hash_key_filter: Фильтр по hash_key
            deal_key_filter: Фильтр по deal_key (частичное совпадение)
            client_filter: Фильтр по клиенту (частичное совпадение)
            order_by: Поле для сортировки
            order_direction: Направление сортировки (asc/desc)
        
        Returns:
            Tuple[список позиций, общее количество]
        """
        
        # Базовый запрос
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
        )
        
        # Запрос для подсчета общего количества
        count_query = select(func.count()).select_from(ReadModelPosition)
        
        # Применяем фильтры
        filters = []
        
        if hash_key_filter:
            filters.append(ReadModelPosition.hash_key == hash_key_filter)
        
        if deal_key_filter:
            filters.append(ReadModelPosition.deal_key.ilike(f"%{deal_key_filter}%"))
        
        if client_filter:
            filters.append(ReadModelPosition.client_name.ilike(f"%{client_filter}%"))
        
        if filters:
            for filter_condition in filters:
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)
        
        # Получаем общее количество
        total_count = await session.scalar(count_query)
        
        # Применяем сортировку
        order_column = getattr(ReadModelPosition, order_by, ReadModelPosition.created_at)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Применяем пагинацию
        if offset > 0:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        # Выполняем запрос
        result = await session.execute(query)
        positions = result.fetchall()
        
        # Конвертируем в список словарей
        positions_data = []
        for pos in positions:
            positions_data.append({
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
                'created_at': pos.created_at.isoformat() if pos.created_at else None,
                'updated_at': pos.updated_at.isoformat() if pos.updated_at else None
            })
        
        return positions_data, total_count or 0
    
    async def export_to_csv(self, positions: list[dict], filename: str) -> None:
        """Экспортирует позиции в CSV файл."""
        
        if not positions:
            print("Нет данных для экспорта")
            return
        
        output_file = Path(__file__).parent / filename
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = positions[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for position in positions:
                writer.writerow(position)
        
        print(f"📄 Данные экспортированы в CSV: {output_file}")
    
    async def export_to_json(self, positions: list[dict], filename: str) -> None:
        """Экспортирует позиции в JSON файл."""
        
        output_file = Path(__file__).parent / filename
        
        export_data = {
            "positions_export": {
                "timestamp": asyncio.get_event_loop().time(),
                "count": len(positions),
                "data": positions
            }
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📄 Данные экспортированы в JSON: {output_file}")
    
    def format_console_output(
        self,
        positions: list[dict],
        total_count: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> str:
        """Форматирует позиции для вывода в консоль."""
        
        output = []
        output.append("=" * 120)
        output.append("📋 ТАБЛИЦА READ_POSITIONS")
        output.append("=" * 120)
        
        # Информация о выборке
        if limit:
            output.append(f"Показано: {len(positions)} из {total_count:,} (с {offset + 1} по {offset + len(positions)})")
        else:
            output.append(f"Показано: {len(positions):,} записей (все)")
        
        output.append("")
        
        if not positions:
            output.append("Нет данных для отображения")
            return "\n".join(output)
        
        # Заголовки таблицы
        headers = [
            "№", "Hash Key", "Deal Key", "Pos#", "Product", "Client", 
            "Revenue", "Created", "Deal ID"
        ]
        
        # Ширины колонок
        widths = [3, 32, 40, 4, 50, 25, 12, 19, 36]
        
        # Печатаем заголовки
        header_line = " | ".join(
            header.ljust(width)[:width] for header, width in zip(headers, widths)
        )
        output.append(header_line)
        output.append("-" * len(header_line))
        
        # Печатаем данные
        for i, pos in enumerate(positions, 1):
            # Сокращаем длинные значения
            deal_key_short = (pos['deal_key'][:37] + "...") if len(pos['deal_key']) > 40 else pos['deal_key']
            product_short = (pos['product_name'][:47] + "...") if len(pos['product_name']) > 50 else pos['product_name']
            client_short = (pos['client_name'][:22] + "...") if len(pos['client_name']) > 25 else pos['client_name']
            
            values = [
                str(i),
                pos['hash_key'][:32],
                deal_key_short,
                str(pos['position_number']),
                product_short,
                client_short,
                f"{pos['revenue_amount']:,.0f}" if pos['revenue_amount'] else "0",
                pos['created_at'][:19] if pos['created_at'] else "",
                str(pos['deal_id'])[:36]
            ]
            
            row_line = " | ".join(
                value.ljust(width)[:width] for value, width in zip(values, widths)
            )
            output.append(row_line)
        
        output.append("")
        output.append("=" * 120)
        
        return "\n".join(output)
    
    async def interactive_view(self) -> None:
        """Интерактивный просмотр с возможностью фильтрации."""
        
        print("🔍 Интерактивный просмотр таблицы read_positions")
        print("=" * 60)
        
        while True:
            print("\nВыберите действие:")
            print("1. Показать все записи")
            print("2. Показать первые N записей")
            print("3. Фильтр по hash_key")
            print("4. Фильтр по deal_key (частичное совпадение)")
            print("5. Фильтр по клиенту (частичное совпадение)")
            print("6. Экспорт в CSV")
            print("7. Экспорт в JSON")
            print("0. Выход")
            
            choice = input("\nВведите номер действия: ").strip()
            
            if choice == "0":
                break
            
            try:
                async with self.db_manager.get_async_session() as session:
                    if choice == "1":
                        # Все записи
                        positions, total_count = await self.get_all_positions(session)
                        output = self.format_console_output(positions, total_count)
                        print(output)
                    
                    elif choice == "2":
                        # Первые N записей
                        limit_str = input("Введите количество записей: ").strip()
                        limit = int(limit_str) if limit_str.isdigit() else 100
                        positions, total_count = await self.get_all_positions(session, limit=limit)
                        output = self.format_console_output(positions, total_count, limit=limit)
                        print(output)
                    
                    elif choice == "3":
                        # Фильтр по hash_key
                        hash_key = input("Введите hash_key: ").strip()
                        if hash_key:
                            positions, total_count = await self.get_all_positions(
                                session, hash_key_filter=hash_key
                            )
                            output = self.format_console_output(positions, total_count)
                            print(output)
                    
                    elif choice == "4":
                        # Фильтр по deal_key
                        deal_key = input("Введите часть deal_key: ").strip()
                        if deal_key:
                            limit_str = input("Лимит записей (Enter = 100): ").strip()
                            limit = int(limit_str) if limit_str.isdigit() else 100
                            positions, total_count = await self.get_all_positions(
                                session, limit=limit, deal_key_filter=deal_key
                            )
                            output = self.format_console_output(positions, total_count, limit=limit)
                            print(output)
                    
                    elif choice == "5":
                        # Фильтр по клиенту
                        client = input("Введите часть имени клиента: ").strip()
                        if client:
                            limit_str = input("Лимит записей (Enter = 100): ").strip()
                            limit = int(limit_str) if limit_str.isdigit() else 100
                            positions, total_count = await self.get_all_positions(
                                session, limit=limit, client_filter=client
                            )
                            output = self.format_console_output(positions, total_count, limit=limit)
                            print(output)
                    
                    elif choice == "6":
                        # Экспорт в CSV
                        limit_str = input("Количество записей для экспорта (Enter = все): ").strip()
                        limit = int(limit_str) if limit_str.isdigit() else None
                        positions, _ = await self.get_all_positions(session, limit=limit)
                        await self.export_to_csv(positions, "positions_export.csv")
                    
                    elif choice == "7":
                        # Экспорт в JSON
                        limit_str = input("Количество записей для экспорта (Enter = все): ").strip()
                        limit = int(limit_str) if limit_str.isdigit() else None
                        positions, _ = await self.get_all_positions(session, limit=limit)
                        await self.export_to_json(positions, "positions_export.json")
            
            except Exception as e:
                print(f"❌ Ошибка: {e}")
    
    async def quick_view(self, limit: int = 50) -> None:
        """Быстрый просмотр первых N записей."""
        
        try:
            async with self.db_manager.get_async_session() as session:
                positions, total_count = await self.get_all_positions(session, limit=limit)
                output = self.format_console_output(positions, total_count, limit=limit)
                print(output)
                
                # Сохраняем также в JSON для детального просмотра
                if positions:
                    await self.export_to_json(positions, f"positions_quick_view_{limit}.json")
                    
        except Exception as e:
            print(f"❌ Ошибка при просмотре данных: {e}")


async def main():
    """Основная функция."""
    
    import sys
    
    viewer = PositionsTableViewer()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            # Быстрый просмотр
            limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 50
            await viewer.quick_view(limit)
        elif sys.argv[1] == "--interactive":
            # Интерактивный режим
            await viewer.interactive_view()
        else:
            print("Использование:")
            print("  python view_positions_table.py --quick [количество]")
            print("  python view_positions_table.py --interactive")
    else:
        # По умолчанию - интерактивный режим
        await viewer.interactive_view()


if __name__ == "__main__":
    asyncio.run(main())