"""
Migration: Fix version duplicates in read_positions table
Date: 2025-01-20
Purpose: 
1. Find and fix records with same hash_key and same version
2. Assign unique version numbers for each hash_key
3. Prepare for (hash_key, version) unique constraint
"""

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger


def _fix_version_duplicates_sqlite(engine: Engine) -> None:
    """Fix version duplicates for SQLite database."""
    with engine.begin() as conn:
        logger.info("Fixing version duplicates in SQLite database")
        
        # Step 1: Find duplicate versions for same hash_key
        duplicates_query = text("""
            SELECT hash_key, version, COUNT(*) as count
            FROM read_positions 
            GROUP BY hash_key, version
            HAVING COUNT(*) > 1
        """)
        
        result = conn.execute(duplicates_query)
        duplicates = result.fetchall()
        
        if not duplicates:
            logger.info("✅ No version duplicates found")
            return
            
        logger.info(f"🔍 Found {len(duplicates)} (hash_key, version) duplicates")
        total_fixed = 0
        
        # Step 2: For each duplicate, fix the versions
        for hash_key, version, count in duplicates:
            logger.info(f"Processing hash_key {hash_key} with version {version} ({count} duplicates)")
            
            # Get all positions with this hash_key and version, ordered by created_at DESC
            positions_query = text("""
                SELECT id, created_at, updated_at
                FROM read_positions 
                WHERE hash_key = :hash_key AND version = :version
                ORDER BY created_at DESC, updated_at DESC
            """)
            
            positions_result = conn.execute(positions_query, {"hash_key": hash_key, "version": version})
            positions = positions_result.fetchall()
            
            if len(positions) <= 1:
                continue
                
            # Find maximum version for this hash_key
            max_version_query = text("""
                SELECT COALESCE(MAX(version), 0) as max_version
                FROM read_positions 
                WHERE hash_key = :hash_key
            """)
            max_version_result = conn.execute(max_version_query, {"hash_key": hash_key})
            max_version = max_version_result.scalar()
            
            # Assign new versions starting from max_version + 1
            next_version = max_version + 1
            
            # Keep the first (newest) record with original version, update others
            for i, position in enumerate(positions[1:], start=1):  # Skip first record
                new_version = next_version + i
                
                update_query = text("""
                    UPDATE read_positions 
                    SET version = :new_version,
                        updated_at = datetime('now')
                    WHERE id = :position_id
                """)
                
                conn.execute(update_query, {
                    "new_version": new_version,
                    "position_id": position.id
                })
                logger.info(f"  📝 Updated record {position.id}: version {version} → {new_version}")
                total_fixed += 1
        
        logger.info(f"✅ Version fix completed: {total_fixed} records updated")
        
        # Step 3: Verify no version duplicates remain
        verify_result = conn.execute(duplicates_query)
        remaining_duplicates = verify_result.fetchall()
        
        if remaining_duplicates:
            logger.error(f"❌ Still have version duplicates after fix: {remaining_duplicates}")
            raise RuntimeError("Version fix failed - duplicates still exist")
        else:
            logger.info("✅ Verification passed: no version duplicates remain")


def _fix_version_duplicates_postgresql(engine: Engine) -> None:
    """Fix version duplicates for PostgreSQL database."""
    with engine.begin() as conn:
        logger.info("Fixing version duplicates in PostgreSQL database")
        
        # Step 1: Find duplicate versions for same hash_key
        duplicates_query = text("""
            SELECT hash_key, version, COUNT(*) as count
            FROM read_positions 
            GROUP BY hash_key, version
            HAVING COUNT(*) > 1
        """)
        
        result = conn.execute(duplicates_query)
        duplicates = result.fetchall()
        
        if not duplicates:
            logger.info("✅ No version duplicates found")
            return
            
        logger.info(f"🔍 Found {len(duplicates)} (hash_key, version) duplicates")
        total_fixed = 0
        
        # Step 2: For each duplicate, fix the versions
        for hash_key, version, count in duplicates:
            logger.info(f"Processing hash_key {hash_key} with version {version} ({count} duplicates)")
            
            # Get all positions with this hash_key and version, ordered by created_at DESC
            positions_query = text("""
                SELECT id, created_at, updated_at
                FROM read_positions 
                WHERE hash_key = :hash_key AND version = :version
                ORDER BY created_at DESC, updated_at DESC
            """)
            
            positions_result = conn.execute(positions_query, {"hash_key": hash_key, "version": version})
            positions = positions_result.fetchall()
            
            if len(positions) <= 1:
                continue
                
            # Find maximum version for this hash_key
            max_version_query = text("""
                SELECT COALESCE(MAX(version), 0) as max_version
                FROM read_positions 
                WHERE hash_key = :hash_key
            """)
            max_version_result = conn.execute(max_version_query, {"hash_key": hash_key})
            max_version = max_version_result.scalar()
            
            # Assign new versions starting from max_version + 1
            next_version = max_version + 1
            
            # Keep the first (newest) record with original version, update others
            for i, position in enumerate(positions[1:], start=1):  # Skip first record
                new_version = next_version + i
                
                update_query = text("""
                    UPDATE read_positions 
                    SET version = :new_version,
                        updated_at = NOW()
                    WHERE id = :position_id
                """)
                
                conn.execute(update_query, {
                    "new_version": new_version,
                    "position_id": position.id
                })
                logger.info(f"  📝 Updated record {position.id}: version {version} → {new_version}")
                total_fixed += 1
        
        logger.info(f"✅ Version fix completed: {total_fixed} records updated")
        
        # Step 3: Verify no version duplicates remain
        verify_result = conn.execute(duplicates_query)
        remaining_duplicates = verify_result.fetchall()
        
        if remaining_duplicates:
            logger.error(f"❌ Still have version duplicates after fix: {remaining_duplicates}")
            raise RuntimeError("Version fix failed - duplicates still exist")
        else:
            logger.info("✅ Verification passed: no version duplicates remain")


def fix_version_duplicates(database_url: str) -> None:
    """Fix version duplicates based on database type."""
    engine = create_engine(database_url)
    
    try:
        if "sqlite" in database_url:
            _fix_version_duplicates_sqlite(engine)
        elif "postgresql" in database_url:
            _fix_version_duplicates_postgresql(engine)
        else:
            raise ValueError(f"Unsupported database type in URL: {database_url}")
            
        logger.info("✅ Version duplicates fix completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Version fix failed: {e}")
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
        logger.info(f"Fixing version duplicates in database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        fix_version_duplicates(database_url)
        
    except Exception as e:
        logger.error(f"Failed to fix version duplicates: {e}")
        sys.exit(1)