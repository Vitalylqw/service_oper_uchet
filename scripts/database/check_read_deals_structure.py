#!/usr/bin/env python3
"""
Check read_deals table structure and understand read_positions field.
"""

import sqlite3
from pathlib import Path

def check_database_structure():
    """Check the structure of read_deals table."""
    db_path = Path("data/service_oper_uchet.sqlite")
    
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(read_deals)")
        columns = cursor.fetchall()
        
        print("=== READ_DEALS TABLE STRUCTURE ===")
        for col in columns:
            cid, name, type_, notnull, default, pk = col
            print(f"{cid:2d}. {name:30s} {type_:15s} {'NOT NULL' if notnull else 'NULL':8s} {'PK' if pk else '':2s} {default if default else ''}")
        
        # Check if read_positions field exists
        read_positions_col = [col for col in columns if col[1] == 'read_positions']
        if read_positions_col:
            print(f"\n✅ Field 'read_positions' found: {read_positions_col[0]}")
        else:
            print(f"\n❌ Field 'read_positions' NOT found in read_deals table")
        
        # Check read_positions table
        cursor.execute("PRAGMA table_info(read_positions)")
        pos_columns = cursor.fetchall()
        
        print(f"\n=== READ_POSITIONS TABLE STRUCTURE ===")
        for col in pos_columns:
            cid, name, type_, notnull, default, pk = col
            print(f"{cid:2d}. {name:30s} {type_:15s} {'NOT NULL' if notnull else 'NULL':8s} {'PK' if pk else '':2s} {default if default else ''}")
        
        # Check sample data
        cursor.execute("SELECT COUNT(*) FROM read_deals")
        deals_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM read_positions")
        positions_count = cursor.fetchone()[0]
        
        print(f"\n=== DATA COUNTS ===")
        print(f"read_deals: {deals_count} records")
        print(f"read_positions: {positions_count} records")
        
        # Check if there are any deals with positions
        if deals_count > 0:
            cursor.execute("""
                SELECT d.id, d.deal_key, d.client_name, COUNT(p.id) as pos_count
                FROM read_deals d
                LEFT JOIN read_positions p ON d.id = p.deal_id
                GROUP BY d.id, d.deal_key, d.client_name
                LIMIT 5
            """)
            sample_deals = cursor.fetchall()
            
            print(f"\n=== SAMPLE DEALS WITH POSITIONS ===")
            for deal_id, deal_key, client_name, pos_count in sample_deals:
                print(f"Deal: {deal_key} | Client: {client_name} | Positions: {pos_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database_structure() 