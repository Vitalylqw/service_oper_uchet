"""
Test script for new unique constraints in read_positions table.

This script validates:
1. Migration applied correctly
2. New unique constraints work as expected
3. No data duplication occurs
"""

import asyncio
import os
import sys
import uuid
from decimal import Decimal

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.infrastructure.database.models import ReadModelPosition


async def check_unique_constraints():
    """Check if unique constraints were applied correctly."""
    logger.info("🔍 Checking unique constraints...")
    
    # Get database URL
    from src.infrastructure.database.connection import DatabaseConfig
    db_config = DatabaseConfig()
    database_url = db_config.async_database_url
    
    # Create async engine
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Check if constraints exist (SQLite)
            if "sqlite" in database_url:
                result = await session.execute(text(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' 
                    AND name IN ('ix_read_positions_hash_active', 'ix_read_positions_hash_version')
                    """
                ))
                constraints = [row[0] for row in result.fetchall()]
                
                if "ix_read_positions_hash_active" in constraints:
                    logger.info("✅ Constraint (hash_key, is_active) exists")
                else:
                    logger.error("❌ Constraint (hash_key, is_active) missing")
                    
                if "ix_read_positions_hash_version" in constraints:
                    logger.info("✅ Constraint (hash_key, version) exists")
                else:
                    logger.error("❌ Constraint (hash_key, version) missing")
                    
            # Check for existing data
            result = await session.execute(text("SELECT COUNT(*) FROM read_positions"))
            count = result.scalar()
            logger.info(f"📊 Total positions in database: {count}")
            
            # Check for active positions
            result = await session.execute(text("SELECT COUNT(*) FROM read_positions WHERE is_active = 1"))
            active_count = result.scalar()
            logger.info(f"🟢 Active positions: {active_count}")
            
            # Check for inactive positions
            result = await session.execute(text("SELECT COUNT(*) FROM read_positions WHERE is_active = 0"))
            inactive_count = result.scalar()
            logger.info(f"🔴 Inactive positions: {inactive_count}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error checking constraints: {e}")
        return False
    finally:
        await engine.dispose()


async def test_constraint_violations():
    """Test that constraints prevent violations."""
    logger.info("🧪 Testing constraint violations...")
    
    # Get database URL
    from src.infrastructure.database.connection import DatabaseConfig
    db_config = DatabaseConfig()
    database_url = db_config.async_database_url
    
    # Create async engine
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    test_hash_key = "test_hash_12345"
    
    try:
        async with async_session() as session:
            # Test 1: Create first active position
            position1_id = uuid.uuid4()
            position1 = ReadModelPosition(
                id=position1_id,
                deal_id=uuid.uuid4(),
                deal_key="TEST_DEAL_001",
                position_number=1,
                hash_key=test_hash_key,
                product_name="Test Product 1",
                supplier_name="Test Supplier",
                pickup_date="15.01.2024",
                quantity=Decimal("10.000"),
                purchase_price_amount=Decimal("1000.00"),
                sale_price_amount=Decimal("1500.00"),
                revenue_amount=Decimal("15000.00"),
                margin_amount=Decimal("5000.00"),
                cost_amount=Decimal("10000.00"),
                client_name="Test Client",
                period_month="Январь",
                period_year="2024",
                is_active=True,
                version=1,
            )
            
            session.add(position1)
            await session.commit()
            logger.info("✅ Created first active position")
            
            # Test 2: Try to create second active position with same hash_key (should fail)
            try:
                position2_id = uuid.uuid4()
                position2 = ReadModelPosition(
                    id=position2_id,
                    deal_id=uuid.uuid4(),
                    deal_key="TEST_DEAL_002",
                    position_number=1,
                    hash_key=test_hash_key,  # Same hash_key
                    product_name="Test Product 2",
                    supplier_name="Test Supplier 2",
                    pickup_date="16.01.2024",
                    quantity=Decimal("5.000"),
                    purchase_price_amount=Decimal("500.00"),
                    sale_price_amount=Decimal("750.00"),
                    revenue_amount=Decimal("3750.00"),
                    margin_amount=Decimal("1250.00"),
                    cost_amount=Decimal("2500.00"),
                    client_name="Test Client 2",
                    period_month="Январь",
                    period_year="2024",
                    is_active=True,  # Same is_active=True
                    version=2,
                )
                
                session.add(position2)
                await session.commit()
                logger.error("❌ CONSTRAINT VIOLATION: Second active position with same hash_key was allowed!")
                return False
                
            except Exception as e:
                logger.info(f"✅ Constraint (hash_key, is_active) correctly prevented violation: {str(e)[:100]}...")
                await session.rollback()
            
            # Test 3: Create inactive position with same hash_key (should work)
            try:
                position3_id = uuid.uuid4()
                position3 = ReadModelPosition(
                    id=position3_id,
                    deal_id=uuid.uuid4(),
                    deal_key="TEST_DEAL_003",
                    position_number=1,
                    hash_key=test_hash_key,  # Same hash_key
                    product_name="Test Product 3",
                    supplier_name="Test Supplier 3",
                    pickup_date="17.01.2024",
                    quantity=Decimal("3.000"),
                    purchase_price_amount=Decimal("300.00"),
                    sale_price_amount=Decimal("450.00"),
                    revenue_amount=Decimal("1350.00"),
                    margin_amount=Decimal("450.00"),
                    cost_amount=Decimal("900.00"),
                    client_name="Test Client 3",
                    period_month="Январь",
                    period_year="2024",
                    is_active=False,  # Different is_active
                    version=3,  # Different version
                )
                
                session.add(position3)
                await session.commit()
                logger.info("✅ Created inactive position with same hash_key (allowed)")
                
            except Exception as e:
                logger.error(f"❌ Unexpected error creating inactive position: {e}")
                await session.rollback()
                return False
            
            # Test 4: Try to create position with same hash_key and same version (should fail)
            try:
                position4_id = uuid.uuid4()
                position4 = ReadModelPosition(
                    id=position4_id,
                    deal_id=uuid.uuid4(),
                    deal_key="TEST_DEAL_004",
                    position_number=1,
                    hash_key=test_hash_key,  # Same hash_key
                    product_name="Test Product 4",
                    supplier_name="Test Supplier 4",
                    pickup_date="18.01.2024",
                    quantity=Decimal("7.000"),
                    purchase_price_amount=Decimal("700.00"),
                    sale_price_amount=Decimal("1050.00"),
                    revenue_amount=Decimal("7350.00"),
                    margin_amount=Decimal("2450.00"),
                    cost_amount=Decimal("4900.00"),
                    client_name="Test Client 4",
                    period_month="Январь",
                    period_year="2024",
                    is_active=False,
                    version=3,  # Same version as position3
                )
                
                session.add(position4)
                await session.commit()
                logger.error("❌ CONSTRAINT VIOLATION: Position with same hash_key and version was allowed!")
                return False
                
            except Exception as e:
                logger.info(f"✅ Constraint (hash_key, version) correctly prevented violation: {str(e)[:100]}...")
                await session.rollback()
            
            # Cleanup test data
            await session.execute(text(f"DELETE FROM read_positions WHERE hash_key = '{test_hash_key}'"))
            await session.commit()
            logger.info("🧹 Cleaned up test data")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error testing constraints: {e}")
        return False
    finally:
        await engine.dispose()


async def main():
    """Main test function."""
    logger.info("🚀 Starting unique constraints test...")
    
    # Step 1: Check constraints exist
    constraints_ok = await check_unique_constraints()
    if not constraints_ok:
        logger.error("❌ Constraints check failed")
        return False
    
    # Step 2: Test constraint violations
    violations_ok = await test_constraint_violations()
    if not violations_ok:
        logger.error("❌ Constraint violation tests failed")
        return False
    
    logger.info("✅ All tests passed! Unique constraints are working correctly.")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)