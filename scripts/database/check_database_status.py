#!/usr/bin/env python3
"""
Simple database status checker.
"""

import sqlite3
import os
from pathlib import Path


def check_database_status():
    """Check the current status of the database."""
    # Get database path
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "service_oper_uchet.sqlite"
    
    if not db_path.exists():
        print("❌ Database file not found!")
        return
    
    print(f"📊 Database: {db_path}")
    print(f"📏 Size: {db_path.stat().st_size / (1024*1024):.2f} MB")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📋 Tables and row counts:")
        print("-" * 40)
        
        total_rows = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_rows += count
            print(f"  {table}: {count} rows")
        
        print("-" * 40)
        print(f"  Total rows: {total_rows}")
        
        if total_rows == 0:
            print("✅ Database is completely empty!")
        else:
            print("⚠️  Database still contains some data")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")


if __name__ == "__main__":
    check_database_status() 