import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from application.excel_parser.parser import ExcelParserService
from domain.models.sync_session import SyncSession, SyncType
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from sqlalchemy import text
import httpx


class JSONReportGenerator:
    """Генератор JSON отчетов с одинаковой структурой для парсера и БД"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent
        self.excel_file = Path(__file__).parent.parent / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"
        
    async def generate_parser_report(self) -> Dict[str, Any]:
        """Генерирует JSON отчет на основе парсинга Excel файла"""
        print("Генерация отчета парсера...")
        
        # Создаем сессию для статистики
        session = SyncSession(
            sync_type=SyncType.MANUAL,
            source_file_path=str(self.excel_file),
            created_by="json_report_generator"
        )
        
        # Парсим Excel файл
        parser_service = ExcelParserService()
        parse_result = await parser_service.parse_file(str(self.excel_file), session)
        deals = parse_result.deals
        
        # Рассчитываем статистику
        stats = self._calculate_parser_statistics(deals, session)
        
        return {
            "report_type": "parser",
            "generated_at": datetime.now().isoformat(),
            "source_file": str(self.excel_file),
            "summary": {
                "total_deals": len(deals),
                "total_items": sum(len(deal.items) for deal in deals),
                "total_revenue": float(sum(deal.total_revenue.amount for deal in deals if deal.total_revenue)),
                "total_margin": float(sum(deal.total_margin.amount for deal in deals if deal.total_margin)),
                "average_revenue_per_deal": float(sum(deal.total_revenue.amount for deal in deals if deal.total_revenue) / len(deals)) if deals else 0,
                "average_margin_per_deal": float(sum(deal.total_margin.amount for deal in deals if deal.total_margin) / len(deals)) if deals else 0
            },
            "financial_metrics": {
                "total_revenue": float(sum(deal.total_revenue.amount for deal in deals if deal.total_revenue)),
                "total_margin": float(sum(deal.total_margin.amount for deal in deals if deal.total_margin)),
                "margin_percentage": float(sum(deal.total_margin.amount for deal in deals if deal.total_margin) / sum(deal.total_revenue.amount for deal in deals if deal.total_revenue) * 100) if sum(deal.total_revenue.amount for deal in deals if deal.total_revenue) > 0 else 0,
                "average_item_price": float(sum(item.sale_price.amount for deal in deals for item in deal.items if item.sale_price) / sum(len(deal.items) for deal in deals)) if sum(len(deal.items) for deal in deals) > 0 else 0
            },
            "period_statistics": self._calculate_period_statistics(deals),
            "client_statistics": self._calculate_client_statistics(deals),
            "recent_deals": [
                {
                    "id": str(deal.id),
                    "client_name": deal.client_name,
                    "invoice_number": deal.invoice_number,
                    "revenue": float(deal.total_revenue.amount) if deal.total_revenue else 0,
                    "margin": float(deal.total_margin.amount) if deal.total_margin else 0,
                    "items_count": len(deal.items),
                    "period": f"{deal.period.year}-{deal.period.month}"
                }
                for deal in deals[:10]  # Последние 10 сделок
            ],
            "sync_session": {
                "id": str(session.id),
                "sync_type": session.sync_type.value,
                "status": session.status.value,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "source_file": session.source_file_path
            }
        }
    
    async def generate_db_report(self) -> Dict[str, Any]:
        """Генерирует JSON отчет на основе данных из БД"""
        print("Генерация отчета БД...")
        
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        async with db_manager.get_async_session() as session:
            # Получаем данные из БД
            deals_data = await self._get_deals_data(session)
            sync_sessions_data = await self._get_sync_sessions_data(session)
            events_data = await self._get_events_data(session)
            api_data = await self._get_api_data()
            
            return {
                "report_type": "database",
                "generated_at": datetime.now().isoformat(),
                "source_file": "database",
                "summary": {
                    "total_deals": deals_data.get("total_deals", 0),
                    "total_items": deals_data.get("total_items", 0),
                    "total_revenue": float(deals_data.get("total_revenue", 0)),
                    "total_margin": float(deals_data.get("total_margin", 0)),
                    "average_revenue_per_deal": float(deals_data.get("average_revenue_per_deal", 0)),
                    "average_margin_per_deal": float(deals_data.get("average_margin_per_deal", 0))
                },
                "financial_metrics": {
                    "total_revenue": float(deals_data.get("total_revenue", 0)),
                    "total_margin": float(deals_data.get("total_margin", 0)),
                    "margin_percentage": float(deals_data.get("margin_percentage", 0)),
                    "average_item_price": float(deals_data.get("average_item_price", 0))
                },
                "period_statistics": deals_data.get("period_statistics", {}),
                "client_statistics": deals_data.get("client_statistics", {}),
                "recent_deals": deals_data.get("recent_deals", []),
                "sync_session": sync_sessions_data.get("latest_session", {}),
                "database_stats": {
                    "total_sync_sessions": sync_sessions_data.get("total_sessions", 0),
                    "total_events": events_data.get("total_events", 0),
                    "api_status": api_data.get("health_status", "unknown")
                }
            }
    
    def _calculate_parser_statistics(self, deals: List, session: SyncSession) -> Dict[str, Any]:
        """Рассчитывает статистику для парсера"""
        if not deals:
            return {}
            
        total_revenue = sum(deal.total_revenue.amount for deal in deals if deal.total_revenue)
        total_margin = sum(deal.total_margin.amount for deal in deals if deal.total_margin)
        total_items = sum(len(deal.items) for deal in deals)
        
        return {
            "total_deals": len(deals),
            "total_items": total_items,
            "total_revenue": float(total_revenue),
            "total_margin": float(total_margin),
            "margin_percentage": float(total_margin / total_revenue * 100) if total_revenue > 0 else 0
        }
    
    def _calculate_period_statistics(self, deals: List) -> Dict[str, Any]:
        """Рассчитывает статистику по периодам"""
        month_to_num = {
            "Январь": "01", "Февраль": "02", "Март": "03", "Апрель": "04",
            "Май": "05", "Июнь": "06", "Июль": "07", "Август": "08",
            "Сентябрь": "09", "Октябрь": "10", "Ноябрь": "11", "Декабрь": "12"
        }
        
        period_stats = {}
        for deal in deals:
            period_key = f"{deal.period.year}-{month_to_num.get(deal.period.month, '00')}"
            if period_key not in period_stats:
                period_stats[period_key] = {
                    "deals_count": 0,
                    "total_revenue": 0.0,
                    "total_margin": 0.0,
                    "items_count": 0
                }
            
            period_stats[period_key]["deals_count"] += 1
            period_stats[period_key]["total_revenue"] += float(deal.total_revenue.amount) if deal.total_revenue else 0
            period_stats[period_key]["total_margin"] += float(deal.total_margin.amount) if deal.total_margin else 0
            period_stats[period_key]["items_count"] += len(deal.items)
        
        return period_stats
    
    def _calculate_client_statistics(self, deals: List) -> Dict[str, Any]:
        """Рассчитывает статистику по клиентам"""
        client_stats = {}
        for deal in deals:
            if deal.client_name not in client_stats:
                client_stats[deal.client_name] = {
                    "deals_count": 0,
                    "total_revenue": 0.0,
                    "total_margin": 0.0,
                    "items_count": 0
                }
            
            client_stats[deal.client_name]["deals_count"] += 1
            client_stats[deal.client_name]["total_revenue"] += float(deal.total_revenue.amount) if deal.total_revenue else 0
            client_stats[deal.client_name]["total_margin"] += float(deal.total_margin.amount) if deal.total_margin else 0
            client_stats[deal.client_name]["items_count"] += len(deal.items)
        
        return client_stats
    
    async def _get_deals_data(self, session) -> Dict[str, Any]:
        """Получает данные о сделках из БД"""
        try:
            # Общая статистика
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_deals,
                    SUM(items_count) as total_items,
                    SUM(total_revenue_amount) as total_revenue,
                    SUM(total_margin_amount) as total_margin,
                    AVG(total_revenue_amount) as avg_revenue,
                    AVG(total_margin_amount) as avg_margin
                FROM read_deals
            """))
            row = result.fetchone()
            
            if not row or row[0] == 0:
                return {
                    "total_deals": 0,
                    "total_items": 0,
                    "total_revenue": 0,
                    "total_margin": 0,
                    "average_revenue_per_deal": 0,
                    "average_margin_per_deal": 0,
                    "margin_percentage": 0,
                    "average_item_price": 0,
                    "period_statistics": {},
                    "client_statistics": {},
                    "recent_deals": []
                }
            
            total_revenue = float(row[2] or 0)
            total_margin = float(row[3] or 0)
            
            # Статистика по периодам
            result = await session.execute(text("""
                SELECT 
                    period_full_name as period,
                    COUNT(*) as deals_count,
                    SUM(total_revenue_amount) as total_revenue,
                    SUM(total_margin_amount) as total_margin,
                    SUM(items_count) as items_count
                FROM read_deals
                GROUP BY period_full_name
                ORDER BY period_full_name
            """))
            period_stats = {}
            for row in result.fetchall():
                period_stats[row[0]] = {
                    "deals_count": row[1],
                    "total_revenue": float(row[2] or 0),
                    "total_margin": float(row[3] or 0),
                    "items_count": row[4]
                }
            
            # Статистика по клиентам
            result = await session.execute(text("""
                SELECT 
                    client_name,
                    COUNT(*) as deals_count,
                    SUM(total_revenue_amount) as total_revenue,
                    SUM(total_margin_amount) as total_margin,
                    SUM(items_count) as items_count
                FROM read_deals
                GROUP BY client_name
                ORDER BY total_revenue DESC
            """))
            client_stats = {}
            for row in result.fetchall():
                client_stats[row[0]] = {
                    "deals_count": row[1],
                    "total_revenue": float(row[2] or 0),
                    "total_margin": float(row[3] or 0),
                    "items_count": row[4]
                }
            
            # Последние сделки
            result = await session.execute(text("""
                SELECT 
                    id, client_name, invoice_number, total_revenue_amount, total_margin_amount, items_count, period_full_name
                FROM read_deals
                ORDER BY created_at DESC
                LIMIT 10
            """))
            recent_deals = []
            for row in result.fetchall():
                recent_deals.append({
                    "id": row[0],
                    "client_name": row[1],
                    "invoice_number": row[2],
                    "revenue": float(row[3] or 0),
                    "margin": float(row[4] or 0),
                    "items_count": row[5],
                    "period": row[6]
                })
            
            return {
                "total_deals": row[0],
                "total_items": row[1] or 0,
                "total_revenue": total_revenue,
                "total_margin": total_margin,
                "average_revenue_per_deal": float(row[4] or 0),
                "average_margin_per_deal": float(row[5] or 0),
                "margin_percentage": float(total_margin / total_revenue * 100) if total_revenue > 0 else 0,
                "average_item_price": float(total_revenue / (row[1] or 1)) if row[1] and row[1] > 0 else 0,
                "period_statistics": period_stats,
                "client_statistics": client_stats,
                "recent_deals": recent_deals
            }
            
        except Exception as e:
            print(f"Ошибка при получении данных о сделках: {e}")
            return {}
    
    async def _get_sync_sessions_data(self, session) -> Dict[str, Any]:
        """Получает данные о сессиях синхронизации"""
        try:
            # Общее количество сессий
            result = await session.execute(text("SELECT COUNT(*) FROM sync_sessions"))
            total_sessions = result.fetchone()[0]
            
            # Последняя сессия
            result = await session.execute(text("""
                SELECT id, sync_type, status, created_at, file_path, stats_data
                FROM sync_sessions
                ORDER BY created_at DESC
                LIMIT 1
            """))
            latest_session = {}
            row = result.fetchone()
            if row:
                latest_session = {
                    "id": row[0],
                    "sync_type": row[1],
                    "status": row[2],
                    "created_at": row[3],
                    "source_file": row[4],
                    "stats_data": row[5]  # Оставляем как есть, не парсим JSON
                }
            
            return {
                "total_sessions": total_sessions,
                "latest_session": latest_session
            }
            
        except Exception as e:
            print(f"Ошибка при получении данных о сессиях: {e}")
            return {}
    
    async def _get_events_data(self, session) -> Dict[str, Any]:
        """Получает данные о событиях"""
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM event_store"))
            total_events = result.fetchone()[0]
            
            return {
                "total_events": total_events
            }
            
        except Exception as e:
            print(f"Ошибка при получении данных о событиях: {e}")
            return {}
    
    async def _get_api_data(self) -> Dict[str, Any]:
        """Получает данные API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health")
                return {
                    "health_status": "healthy" if response.status_code == 200 else "unhealthy"
                }
        except Exception as e:
            print(f"Ошибка при проверке API: {e}")
            return {
                "health_status": "unavailable"
            }
    
    async def generate_reports(self):
        """Генерирует оба отчета и сохраняет их в JSON файлы"""
        print("Начинаю генерацию JSON отчетов...")
        
        # Генерируем отчет парсера
        parser_report = await self.generate_parser_report()
        parser_file = self.output_dir / "parser_report.json"
        with open(parser_file, 'w', encoding='utf-8') as f:
            json.dump(parser_report, f, ensure_ascii=False, indent=2)
        print(f"Отчет парсера сохранен: {parser_file}")
        
        # Генерируем отчет БД
        db_report = await self.generate_db_report()
        db_file = self.output_dir / "database_report.json"
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(db_report, f, ensure_ascii=False, indent=2)
        print(f"Отчет БД сохранен: {db_file}")
        
        # Создаем краткое сравнение
        comparison = self._create_comparison(parser_report, db_report)
        comparison_file = self.output_dir / "comparison.json"
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        print(f"Сравнение сохранено: {comparison_file}")
        
        print("Генерация отчетов завершена!")
    
    def _create_comparison(self, parser_report: Dict[str, Any], db_report: Dict[str, Any]) -> Dict[str, Any]:
        """Создает сравнение между отчетами"""
        return {
            "comparison_type": "parser_vs_database",
            "generated_at": datetime.now().isoformat(),
            "summary_comparison": {
                "total_deals": {
                    "parser": parser_report["summary"]["total_deals"],
                    "database": db_report["summary"]["total_deals"],
                    "difference": parser_report["summary"]["total_deals"] - db_report["summary"]["total_deals"]
                },
                "total_items": {
                    "parser": parser_report["summary"]["total_items"],
                    "database": db_report["summary"]["total_items"],
                    "difference": parser_report["summary"]["total_items"] - db_report["summary"]["total_items"]
                },
                "total_revenue": {
                    "parser": parser_report["summary"]["total_revenue"],
                    "database": db_report["summary"]["total_revenue"],
                    "difference": parser_report["summary"]["total_revenue"] - db_report["summary"]["total_revenue"]
                },
                "total_margin": {
                    "parser": parser_report["summary"]["total_margin"],
                    "database": db_report["summary"]["total_margin"],
                    "difference": parser_report["summary"]["total_margin"] - db_report["summary"]["total_margin"]
                }
            },
            "financial_comparison": {
                "margin_percentage": {
                    "parser": parser_report["financial_metrics"]["margin_percentage"],
                    "database": db_report["financial_metrics"]["margin_percentage"],
                    "difference": parser_report["financial_metrics"]["margin_percentage"] - db_report["financial_metrics"]["margin_percentage"]
                }
            }
        }


async def main():
    """Основная функция"""
    generator = JSONReportGenerator()
    await generator.generate_reports()


if __name__ == "__main__":
    asyncio.run(main()) 