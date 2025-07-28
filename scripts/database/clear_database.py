#!/usr/bin/env python3
"""
Database cleanup script for service_oper_uchet.

This script clears all data from the SQLite database while preserving the schema structure.
"""

import sqlite3
import os
import sys
from pathlib import Path
from typing import List, Tuple
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    # Get the project root directory (two levels up from this script)
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "service_oper_uchet.sqlite"
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    return db_path


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """Get all table names from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_foreign_key_constraints(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    """Get foreign key constraints to understand table dependencies."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_key_list(sqlite_master)")
    constraints = cursor.fetchall()
    cursor.close()
    
    # Extract table and referenced table names
    fk_constraints = []
    for constraint in constraints:
        if len(constraint) >= 4:
            fk_constraints.append((constraint[2], constraint[3]))  # table, referenced_table
    
    return fk_constraints


def clear_table_data(conn: sqlite3.Connection, table_name: str) -> int:
    """Clear all data from a specific table."""
    cursor = conn.cursor()
    
    # Get row count before deletion
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    
    # Delete all rows
    cursor.execute(f"DELETE FROM {table_name}")
    deleted_rows = cursor.rowcount
    
    # Reset auto-increment counters
    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
    
    cursor.close()
    return deleted_rows


def clear_database(db_path: Path) -> None:
    """Clear all data from the database while preserving schema."""
    logger.info(f"Starting database cleanup for: {db_path}")
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return
    
    # Get file size before cleanup
    file_size_before = db_path.stat().st_size
    logger.info(f"Database size before cleanup: {file_size_before / (1024*1024):.2f} MB")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = OFF")  # Disable foreign key constraints
        
        # Get all table names
        tables = get_table_names(conn)
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Clear data from each table
        total_deleted = 0
        for table in tables:
            try:
                deleted_rows = clear_table_data(conn, table)
                total_deleted += deleted_rows
                logger.info(f"Cleared {deleted_rows} rows from table '{table}'")
            except Exception as e:
                logger.error(f"Error clearing table '{table}': {e}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # Get file size after cleanup
        file_size_after = db_path.stat().st_size
        logger.info(f"Database size after cleanup: {file_size_after / (1024*1024):.2f} MB")
        logger.info(f"Total rows deleted: {total_deleted}")
        
        # Perform VACUUM to reclaim space
        logger.info("Starting VACUUM operation to reclaim space...")
        start_time = time.time()
        
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Get final file size
        file_size_final = db_path.stat().st_size
        space_reclaimed = file_size_after - file_size_final
        space_reclaimed_mb = space_reclaimed / (1024*1024)
        
        logger.info(f"VACUUM completed in {duration:.2f} seconds")
        logger.info(f"Final database size: {file_size_final / (1024*1024):.2f} MB")
        logger.info(f"Space reclaimed: {space_reclaimed_mb:.2f} MB")
        logger.info("Database cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        raise


def main():
    """Main function to run the database cleanup."""
    try:
        db_path = get_database_path()
        clear_database(db_path)
        print("✅ Database cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Failed to cleanup database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 