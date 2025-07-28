#!/usr/bin/env python3
"""
Database structure analyzer to understand why empty DB is so large.
"""

import sqlite3
import os
from pathlib import Path


def analyze_database_structure():
    """Analyze the database structure in detail."""
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
        
        # Get database info
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA freelist_count")
        freelist_count = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA auto_vacuum")
        auto_vacuum = cursor.fetchone()[0]
        
        print("🔍 Database Structure Analysis:")
        print("-" * 50)
        print(f"  Page count: {page_count:,}")
        print(f"  Page size: {page_size:,} bytes")
        print(f"  Freelist pages: {freelist_count:,}")
        print(f"  Auto vacuum: {auto_vacuum}")
        print(f"  Calculated size: {page_count * page_size / (1024*1024):.2f} MB")
        print()
        
        # Get all tables with their structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📋 Tables Structure:")
        print("-" * 50)
        
        total_columns = 0
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            print(f"\n  Table: {table}")
            print(f"    Columns: {len(columns)}")
            total_columns += len(columns)
            
            for col in columns:
                col_id, name, type_name, not_null, default_val, pk = col
                print(f"      {name}: {type_name}")
        
        print(f"\n  Total columns across all tables: {total_columns}")
        
        # Check for indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        print(f"\n🔍 Indexes ({len(indexes)}):")
        for idx in indexes:
            print(f"  - {idx}")
        
        # Check for triggers
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        triggers = [row[0] for row in cursor.fetchall()]
        
        print(f"\n🔍 Triggers ({len(triggers)}):")
        for trigger in triggers:
            print(f"  - {trigger}")
        
        # Check for views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [row[0] for row in cursor.fetchall()]
        
        print(f"\n🔍 Views ({len(views)}):")
        for view in views:
            print(f"  - {view}")
        
        conn.close()
        
        print(f"\n💡 Analysis:")
        print(f"  - Large size likely due to many freelist pages from deleted data")
        print(f"  - SQLite doesn't automatically reclaim space after DELETE operations")
        print(f"  - Need VACUUM to reclaim space")
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")


if __name__ == "__main__":
    analyze_database_structure() 