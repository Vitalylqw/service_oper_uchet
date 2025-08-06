"""
Migration: Cleanup duplicate positions before adding unique constraints
Date: 2025-01-20
Purpose: 
1. Find and deactivate duplicate active positions with same hash_key
2. Keep only the latest version of each position
3. Prepare database for unique constraints
"""

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger


def _cleanup_sqlite(engine: Engine) -> None:
    """Cleanup duplicates for SQLite database."""
    with engine.begin() as conn:
        logger.info("Cleaning up duplicate positions in SQLite database")
        
        # Step 1: Find duplicate active positions
        duplicates_query = text("""
            SELECT hash_key, COUNT(*) as count
            FROM read_positions 
            WHERE is_active = 1
            GROUP BY hash_key
            HAVING COUNT(*) > 1
        """)
        
        result = conn.execute(duplicates_query)
        duplicates = result.fetchall()
        
        if not duplicates:
            logger.info("✅ No duplicate active positions found")
            return
            
        logger.info(f"🔍 Found {len(duplicates)} hash_keys with duplicates")
        total_deactivated = 0
        
        # Step 2: For each duplicate hash_key, keep only one active record
        for hash_key, count in duplicates:
            logger.info(f"Processing hash_key {hash_key} with {count} duplicates")
            
            # Get all positions with this hash_key, ordered by created_at DESC
            positions_query = text("""
                SELECT id, deal_id, version, created_at
                FROM read_positions 
                WHERE hash_key = :hash_key AND is_active = 1
                ORDER BY created_at DESC, version DESC
            """)
            
            positions_result = conn.execute(positions_query, {"hash_key": hash_key})
            positions = positions_result.fetchall()
            
            if len(positions) <= 1:
                continue
                
            # Keep the first (latest) record, deactivate others
            keep_record = positions[0]
            deactivate_records = positions[1:]
            
            logger.info(f"  📌 Keeping record: {keep_record.id} (created: {keep_record.created_at})")
            
            for record in deactivate_records:
                # Deactivate old record with version increment
                deactivate_query = text("""
                    UPDATE read_positions 
                    SET is_active = 0, 
                        version = version + 1,
                        updated_at = datetime('now')
                    WHERE id = :record_id
                """)
                
                conn.execute(deactivate_query, {"record_id": record.id})
                logger.info(f"  🔴 Deactivated record: {record.id} (created: {record.created_at})")
                total_deactivated += 1
        
        logger.info(f"✅ Cleanup completed: {total_deactivated} duplicate records deactivated")
        
        # Step 3: Verify no duplicates remain
        verify_result = conn.execute(duplicates_query)
        remaining_duplicates = verify_result.fetchall()
        
        if remaining_duplicates:
            logger.error(f"❌ Still have duplicates after cleanup: {remaining_duplicates}")
            raise RuntimeError("Cleanup failed - duplicates still exist")
        else:
            logger.info("✅ Verification passed: no active duplicates remain")


def _cleanup_postgresql(engine: Engine) -> None:
    """Cleanup duplicates for PostgreSQL database."""
    with engine.begin() as conn:
        logger.info("Cleaning up duplicate positions in PostgreSQL database")
        
        # Step 1: Find duplicate active positions
        duplicates_query = text("""
            SELECT hash_key, COUNT(*) as count
            FROM read_positions 
            WHERE is_active = true
            GROUP BY hash_key
            HAVING COUNT(*) > 1
        """)
        
        result = conn.execute(duplicates_query)
        duplicates = result.fetchall()
        
        if not duplicates:
            logger.info("✅ No duplicate active positions found")
            return
            
        logger.info(f"🔍 Found {len(duplicates)} hash_keys with duplicates")
        total_deactivated = 0
        
        # Step 2: For each duplicate hash_key, keep only one active record
        for hash_key, count in duplicates:
            logger.info(f"Processing hash_key {hash_key} with {count} duplicates")
            
            # Get all positions with this hash_key, ordered by created_at DESC
            positions_query = text("""
                SELECT id, deal_id, version, created_at
                FROM read_positions 
                WHERE hash_key = :hash_key AND is_active = true
                ORDER BY created_at DESC, version DESC
            """)
            
            positions_result = conn.execute(positions_query, {"hash_key": hash_key})
            positions = positions_result.fetchall()
            
            if len(positions) <= 1:
                continue
                
            # Keep the first (latest) record, deactivate others
            keep_record = positions[0]
            deactivate_records = positions[1:]
            
            logger.info(f"  📌 Keeping record: {keep_record.id} (created: {keep_record.created_at})")
            
            for record in deactivate_records:
                # Deactivate old record with version increment
                deactivate_query = text("""
                    UPDATE read_positions 
                    SET is_active = false, 
                        version = version + 1,
                        updated_at = NOW()
                    WHERE id = :record_id
                """)
                
                conn.execute(deactivate_query, {"record_id": record.id})
                logger.info(f"  🔴 Deactivated record: {record.id} (created: {record.created_at})")
                total_deactivated += 1
        
        logger.info(f"✅ Cleanup completed: {total_deactivated} duplicate records deactivated")
        
        # Step 3: Verify no duplicates remain
        verify_result = conn.execute(duplicates_query)
        remaining_duplicates = verify_result.fetchall()
        
        if remaining_duplicates:
            logger.error(f"❌ Still have duplicates after cleanup: {remaining_duplicates}")
            raise RuntimeError("Cleanup failed - duplicates still exist")
        else:
            logger.info("✅ Verification passed: no active duplicates remain")


def cleanup_duplicates(database_url: str) -> None:
    """Cleanup duplicate positions based on database type."""
    engine = create_engine(database_url)
    
    try:
        if "sqlite" in database_url:
            _cleanup_sqlite(engine)
        elif "postgresql" in database_url:
            _cleanup_postgresql(engine)
        else:
            raise ValueError(f"Unsupported database type in URL: {database_url}")
            
        logger.info("✅ Duplicate cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    # Add parent directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, project_root)

    from src.infrastructure.database.connection import DatabaseConfig
    
    try:
        db_config = DatabaseConfig()
        database_url = db_config.sync_database_url
        logger.info(f"Cleaning up duplicates in database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        cleanup_duplicates(database_url)
        
    except Exception as e:
        logger.error(f"Failed to cleanup duplicates: {e}")
        sys.exit(1)