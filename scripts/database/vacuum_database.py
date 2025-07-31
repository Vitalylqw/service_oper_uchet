#!/usr/bin/env python3
"""
Database VACUUM script to reclaim space after data deletion.
"""

import sqlite3
import os
import sys
from pathlib import Path
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
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "service_oper_uchet.sqlite"
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    return db_path


def get_database_stats(conn: sqlite3.Connection) -> dict:
    """Get database statistics before VACUUM."""
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA freelist_count")
    freelist_count = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA auto_vacuum")
    auto_vacuum = cursor.fetchone()[0]
    
    cursor.close()
    
    return {
        'page_count': page_count,
        'page_size': page_size,
        'freelist_count': freelist_count,
        'auto_vacuum': auto_vacuum,
        'total_size_mb': page_count * page_size / (1024*1024),
        'freelist_size_mb': freelist_count * page_size / (1024*1024)
    }


def vacuum_database(db_path: Path) -> None:
    """Perform VACUUM operation on the database."""
    logger.info(f"Starting VACUUM operation for: {db_path}")
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return
    
    # Get file size before VACUUM
    file_size_before = db_path.stat().st_size
    logger.info(f"Database size before VACUUM: {file_size_before / (1024*1024):.2f} MB")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Get stats before VACUUM
        stats_before = get_database_stats(conn)
        logger.info(f"Before VACUUM:")
        logger.info(f"  Total pages: {stats_before['page_count']:,}")
        logger.info(f"  Freelist pages: {stats_before['freelist_count']:,}")
        logger.info(f"  Freelist size: {stats_before['freelist_size_mb']:.2f} MB")
        
        # Perform VACUUM
        logger.info("Starting VACUUM operation...")
        start_time = time.time()
        
        conn.execute("VACUUM")
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"VACUUM completed in {duration:.2f} seconds")
        
        # Get stats after VACUUM
        stats_after = get_database_stats(conn)
        logger.info(f"After VACUUM:")
        logger.info(f"  Total pages: {stats_after['page_count']:,}")
        logger.info(f"  Freelist pages: {stats_after['freelist_count']:,}")
        logger.info(f"  Freelist size: {stats_after['freelist_size_mb']:.2f} MB")
        
        conn.close()
        
        # Get file size after VACUUM
        file_size_after = db_path.stat().st_size
        size_reduction = file_size_before - file_size_after
        size_reduction_mb = size_reduction / (1024*1024)
        
        logger.info(f"Database size after VACUUM: {file_size_after / (1024*1024):.2f} MB")
        logger.info(f"Space reclaimed: {size_reduction_mb:.2f} MB")
        logger.info(f"Reduction: {(size_reduction / file_size_before * 100):.1f}%")
        
        logger.info("VACUUM operation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during VACUUM operation: {e}")
        raise


def main():
    """Main function to run the VACUUM operation."""
    try:
        db_path = get_database_path()
        vacuum_database(db_path)
        print("✅ Database VACUUM completed successfully!")
        
    except Exception as e:
        logger.error(f"Failed to perform VACUUM: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 