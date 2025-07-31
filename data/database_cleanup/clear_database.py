#!/usr/bin/env python3
"""
Enhanced Database Cleanup Script for service_oper_uchet.

This script provides comprehensive database cleanup functionality with:
- Data clearing while preserving schema
- Backup creation before cleanup
- Detailed logging and statistics
- VACUUM operation for space reclamation
- Safety checks and confirmations
"""

import sqlite3
import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging
import time
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / 'database_cleanup.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """Database cleanup utility class."""
    
    def __init__(self, db_path: Path, create_backup: bool = True):
        self.db_path = db_path
        self.create_backup = create_backup
        self.backup_path: Optional[Path] = None
        self.stats: Dict[str, any] = {}
        
    def _create_backup(self) -> None:
        """Create a backup of the database before cleanup."""
        if not self.create_backup:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.db_path.parent / "backup"
        backup_dir.mkdir(exist_ok=True)
        
        backup_name = f"service_oper_uchet_backup_{timestamp}.sqlite"
        self.backup_path = backup_dir / backup_name
        
        logger.info(f"Creating backup: {self.backup_path}")
        shutil.copy2(self.db_path, self.backup_path)
        
        backup_size = self.backup_path.stat().st_size
        logger.info(f"Backup created successfully: {backup_size / (1024*1024):.2f} MB")
        
    def _get_database_info(self) -> Dict[str, any]:
        """Get comprehensive database information."""
        conn = sqlite3.connect(self.db_path)
        
        # Get table names and row counts
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_stats = {}
        total_rows = 0
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            table_stats[table] = row_count
            total_rows += row_count
            
        # Get database size
        file_size = self.db_path.stat().st_size
        
        conn.close()
        
        return {
            'tables': table_stats,
            'total_rows': total_rows,
            'file_size': file_size,
            'table_count': len(tables)
        }
        
    def _clear_table_data(self, conn: sqlite3.Connection, table_name: str) -> int:
        """Clear all data from a specific table."""
        cursor = conn.cursor()
        
        # Get row count before deletion
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        if row_count == 0:
            cursor.close()
            return 0
            
        # Delete all rows
        cursor.execute(f"DELETE FROM {table_name}")
        deleted_rows = cursor.rowcount
        
        # Reset auto-increment counters
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
        
        cursor.close()
        return deleted_rows
        
    def _perform_vacuum(self) -> None:
        """Perform VACUUM operation to reclaim space."""
        logger.info("Starting VACUUM operation to reclaim space...")
        start_time = time.time()
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("VACUUM")
        conn.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"VACUUM completed in {duration:.2f} seconds")
        
    def cleanup(self, confirm: bool = False) -> None:
        """Perform complete database cleanup."""
        logger.info(f"Starting database cleanup for: {self.db_path}")
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
            
        # Get initial database info
        initial_info = self._get_database_info()
        logger.info(f"Database contains {initial_info['total_rows']} rows across {initial_info['table_count']} tables")
        logger.info(f"Database size: {initial_info['file_size'] / (1024*1024):.2f} MB")
        
        # Show table statistics
        for table, count in initial_info['tables'].items():
            if count > 0:
                logger.info(f"  - {table}: {count} rows")
                
        # Create backup if requested
        if self.create_backup:
            self._create_backup()
            
        # Ask for confirmation if not auto-confirmed
        if not confirm:
            response = input("\n⚠️  WARNING: This will delete ALL data from the database!\n"
                           "Are you sure you want to continue? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Cleanup cancelled by user")
                return
                
        try:
            # Connect and disable foreign key constraints
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = OFF")
            
            # Clear data from each table
            total_deleted = 0
            cleared_tables = []
            
            for table in initial_info['tables'].keys():
                try:
                    deleted_rows = self._clear_table_data(conn, table)
                    if deleted_rows > 0:
                        total_deleted += deleted_rows
                        cleared_tables.append(table)
                        logger.info(f"[SUCCESS] Cleared {deleted_rows} rows from table '{table}'")
                except Exception as e:
                    logger.error(f"[ERROR] Error clearing table '{table}': {e}")
                    
            # Commit changes
            conn.commit()
            conn.close()
            
            # Perform VACUUM
            self._perform_vacuum()
            
            # Get final database info
            final_info = self._get_database_info()
            
            # Calculate statistics
            space_saved = initial_info['file_size'] - final_info['file_size']
            space_saved_mb = space_saved / (1024*1024)
            
            # Store statistics
            self.stats = {
                'initial_rows': initial_info['total_rows'],
                'deleted_rows': total_deleted,
                'final_rows': final_info['total_rows'],
                'initial_size_mb': initial_info['file_size'] / (1024*1024),
                'final_size_mb': final_info['file_size'] / (1024*1024),
                'space_saved_mb': space_saved_mb,
                'cleared_tables': cleared_tables,
                'backup_created': self.backup_path is not None,
                'backup_path': str(self.backup_path) if self.backup_path else None
            }
            
            # Log results
            logger.info("=" * 50)
            logger.info("CLEANUP COMPLETED SUCCESSFULLY")
            logger.info("=" * 50)
            logger.info(f"Rows deleted: {total_deleted}")
            logger.info(f"Tables cleared: {len(cleared_tables)}")
            logger.info(f"Space saved: {space_saved_mb:.2f} MB")
            logger.info(f"Final database size: {final_info['file_size'] / (1024*1024):.2f} MB")
            
            if self.backup_path:
                logger.info(f"Backup created: {self.backup_path}")
                
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            raise
            
    def get_stats(self) -> Dict[str, any]:
        """Get cleanup statistics."""
        return self.stats.copy()


def get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    # Script is in database_cleanup directory, so database is one level up
    script_dir = Path(__file__).parent
    db_path = script_dir.parent / "service_oper_uchet.sqlite"
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    return db_path


def main():
    """Main function to run the database cleanup."""
    parser = argparse.ArgumentParser(description="Database cleanup utility")
    parser.add_argument("--no-backup", action="store_true", 
                       help="Skip backup creation")
    parser.add_argument("--confirm", action="store_true",
                       help="Skip confirmation prompt")
    parser.add_argument("--stats-only", action="store_true",
                       help="Show database statistics only")
    
    args = parser.parse_args()
    
    try:
        db_path = get_database_path()
        cleaner = DatabaseCleaner(db_path, create_backup=not args.no_backup)
        
        if args.stats_only:
            # Show database statistics only
            info = cleaner._get_database_info()
            print("\n📊 DATABASE STATISTICS")
            print("=" * 30)
            print(f"Database: {db_path}")
            print(f"Size: {info['file_size'] / (1024*1024):.2f} MB")
            print(f"Tables: {info['table_count']}")
            print(f"Total rows: {info['total_rows']}")
            print("\nTable breakdown:")
            for table, count in info['tables'].items():
                print(f"  - {table}: {count} rows")
            return
            
        # Perform cleanup
        cleaner.cleanup(confirm=args.confirm)
        
        # Show final statistics
        stats = cleaner.get_stats()
        if stats:
            print("\n📈 CLEANUP STATISTICS")
            print("=" * 30)
            print(f"Rows deleted: {stats['deleted_rows']}")
            print(f"Space saved: {stats['space_saved_mb']:.2f} MB")
            print(f"Tables cleared: {len(stats['cleared_tables'])}")
            if stats['backup_created']:
                print(f"Backup: {stats['backup_path']}")
                
        print("\n✅ Database cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Failed to cleanup database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()