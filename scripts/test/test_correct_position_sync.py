"""
Test script for correct position synchronization logic.

Tests the new deal-level position synchronization with:
1. Version-based updates using hash_key comparison
2. Deal-level cleanup of removed positions
3. Proper is_active flag management

Author: System Architect
Date: 2025-01-20
"""

import asyncio
import os
import sys
import uuid
from decimal import Decimal

from loguru import logger

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.domain.models import Deal, DealItem
from src.domain.value_objects import Period, Money, SignedMoney
from src.infrastructure.workers.read_model_position_sync import PositionSyncLogic
from src.infrastructure.database.connection import DatabaseConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.infrastructure.database.models import ReadModelPosition


async def create_test_deal() -> Deal:
    """Create a test deal with positions for testing."""
    period = Period(month="Январь", year="2025", full_name="Январь 2025")
    
    deal = Deal(
        id=uuid.uuid4(),
        deal_key="TEST_DEAL_KEY_2025_001",
        client_name="Тестовый клиент",
        invoice_info="Тестовая накладная",
        invoice_number="TEST-001",
        period=period,
        total_revenue=Money(amount=Decimal("10000")),
        total_margin=SignedMoney(amount=Decimal("2000")),
        total_cost=Money(amount=Decimal("8000")),
        items=[],
    )
    
    # Add test positions
    positions = [
        {
            "product_name": "Товар А",
            "supplier_name": "Поставщик 1",
            "quantity": Decimal("10"),
            "revenue": Decimal("5000"),
            "margin": Decimal("1000"),
            "cost": Decimal("4000"),
        },
        {
            "product_name": "Товар Б", 
            "supplier_name": "Поставщик 2",
            "quantity": Decimal("5"),
            "revenue": Decimal("3000"),
            "margin": Decimal("600"),
            "cost": Decimal("2400"),
        },
        {
            "product_name": "Товар В",
            "supplier_name": "Поставщик 1", 
            "quantity": Decimal("3"),
            "revenue": Decimal("2000"),
            "margin": Decimal("400"),
            "cost": Decimal("1600"),
        },
    ]
    
    for i, pos_data in enumerate(positions):
        item = DealItem(
            id=uuid.uuid4(),
            deal_id=deal.id,
            item_key=pos_data["product_name"],
            product_name=pos_data["product_name"],
            supplier_name=pos_data["supplier_name"],
            quantity=pos_data["quantity"],
            revenue=Money(amount=pos_data["revenue"]),
            margin=SignedMoney(amount=pos_data["margin"]),
            cost=Money(amount=pos_data["cost"]),
        )
        deal.items.append(item)
    
    return deal


async def test_position_sync_logic():
    """Test the new position synchronization logic."""
    logger.info("🧪 Starting position synchronization test")
    
    # Setup database connection
    db_config = DatabaseConfig()
    engine = create_async_engine(db_config.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        sync_logic = PositionSyncLogic(session)
        
        # Step 1: Create initial deal with positions
        logger.info("📝 Step 1: Creating initial deal with 3 positions")
        initial_deal = await create_test_deal()
        
        deal_context = {
            "deal_key": initial_deal.deal_key,
            "client_name": initial_deal.client_name,
            "period_month": initial_deal.period.month,
            "period_year": initial_deal.period.year,
        }
        
        sync_session_id = uuid.uuid4()
        stats1 = await sync_logic.sync_deal_positions(initial_deal, deal_context, sync_session_id)
        await session.commit()
        
        logger.info(f"✅ Initial sync stats: {stats1}")
        
        # Verify initial state
        from sqlalchemy import select, text
        active_positions_result = await session.execute(
            select(ReadModelPosition).where(
                ReadModelPosition.deal_key == initial_deal.deal_key,
                ReadModelPosition.is_active == True
            )
        )
        active_positions_initial = list(active_positions_result.scalars())
        logger.info(f"📊 Active positions after initial sync: {len(active_positions_initial)}")
        
        # Step 2: Update one position and add a new one
        logger.info("📝 Step 2: Updating deal - change one position, add new, remove one")
        
        # Create modified deal
        modified_deal = Deal(
            id=uuid.uuid4(),  # NEW UUID (simulates parser behavior)
            deal_key=initial_deal.deal_key,  # SAME deal_key (identifies deal)
            client_name=initial_deal.client_name,
            invoice_info=initial_deal.invoice_info,
            invoice_number=initial_deal.invoice_number,
            period=initial_deal.period,
            total_revenue=Money(amount=Decimal("12000")),
            total_margin=SignedMoney(amount=Decimal("2400")),
            total_cost=Money(amount=Decimal("9600")),
            items=[],
        )
        
        # Modified positions (remove "Товар В", modify "Товар А", add "Товар Г")
        new_positions = [
            {
                "product_name": "Товар А",  # SAME hash_key, but different quantity
                "supplier_name": "Поставщик 1",
                "quantity": Decimal("15"),  # CHANGED from 10 to 15
                "revenue": Decimal("7500"),
                "margin": Decimal("1500"),
                "cost": Decimal("6000"),
            },
            {
                "product_name": "Товар Б",  # UNCHANGED
                "supplier_name": "Поставщик 2",
                "quantity": Decimal("5"),
                "revenue": Decimal("3000"),
                "margin": Decimal("600"),
                "cost": Decimal("2400"),
            },
            {
                "product_name": "Товар Г",  # NEW position
                "supplier_name": "Поставщик 3",
                "quantity": Decimal("2"),
                "revenue": Decimal("1500"),
                "margin": Decimal("300"),
                "cost": Decimal("1200"),
            },
            # "Товар В" REMOVED from deal
        ]
        
        for pos_data in new_positions:
            item = DealItem(
                id=uuid.uuid4(),
                deal_id=modified_deal.id,
                item_key=pos_data["product_name"],
                product_name=pos_data["product_name"],
                supplier_name=pos_data["supplier_name"],
                quantity=pos_data["quantity"],
                revenue=Money(amount=pos_data["revenue"]),
                margin=SignedMoney(amount=pos_data["margin"]),
                cost=Money(amount=pos_data["cost"]),
            )
            modified_deal.items.append(item)
        
        # Apply changes
        stats2 = await sync_logic.sync_deal_positions(modified_deal, deal_context, sync_session_id)
        await session.commit()
        
        logger.info(f"✅ Update sync stats: {stats2}")
        
        # Step 3: Verify final state
        logger.info("📊 Step 3: Verifying final state")
        
        # Count active positions
        active_result = await session.execute(
            select(ReadModelPosition).where(
                ReadModelPosition.deal_key == initial_deal.deal_key,
                ReadModelPosition.is_active == True
            ).order_by(ReadModelPosition.product_name)
        )
        active_positions = list(active_result.scalars())
        
        # Count all positions (including inactive)
        all_result = await session.execute(
            select(ReadModelPosition).where(
                ReadModelPosition.deal_key == initial_deal.deal_key
            ).order_by(ReadModelPosition.product_name, ReadModelPosition.version)
        )
        all_positions = list(all_result.scalars())
        
        logger.info(f"📈 Final results:")
        logger.info(f"   • Active positions: {len(active_positions)}")
        logger.info(f"   • Total positions (all versions): {len(all_positions)}")
        
        for pos in active_positions:
            logger.info(f"   ✅ Active: {pos.product_name} - qty: {pos.quantity} - v{pos.version}")
        
        # Verify expectations
        expected_active = 3  # "Товар А" (updated), "Товар Б" (unchanged), "Товар Г" (new)
        assert len(active_positions) == expected_active, f"Expected {expected_active} active positions, got {len(active_positions)}"
        
        # Verify "Товар А" was updated (should have higher version)
        tovar_a_positions = [p for p in all_positions if p.product_name == "Товар А"]
        assert len(tovar_a_positions) >= 2, "Товар А should have multiple versions"
        
        # Verify "Товар В" was deactivated
        tovar_v_active = [p for p in active_positions if p.product_name == "Товар В"]
        assert len(tovar_v_active) == 0, "Товар В should be deactivated"
        
        # Verify "Товар Г" was created
        tovar_g_active = [p for p in active_positions if p.product_name == "Товар Г"]
        assert len(tovar_g_active) == 1, "Товар Г should be created"
        
        logger.info("🎉 All tests passed! Position synchronization logic works correctly.")


if __name__ == "__main__":
    asyncio.run(test_position_sync_logic())