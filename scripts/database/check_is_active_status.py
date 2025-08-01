#!/usr/bin/env python3
"""
Check is_active field status in read_deals and read_positions tables.
"""

import sqlite3
from pathlib import Path

def check_is_active_status():
    """Check the status of is_active field in read models."""
    db_path = Path("data/service_oper_uchet.sqlite")
    
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== IS_ACTIVE FIELD STATUS ===")
        
        # Check read_deals table
        cursor.execute("""
            SELECT 
                COUNT(*) as total_deals,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_deals,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_deals
            FROM read_deals
        """)
        deals_stats = cursor.fetchone()
        
        print(f"READ_DEALS:")
        print(f"  Total deals: {deals_stats[0]}")
        print(f"  Active deals (is_active=1): {deals_stats[1]}")
        print(f"  Inactive deals (is_active=0): {deals_stats[2]}")
        
        # Check read_positions table
        cursor.execute("""
            SELECT 
                COUNT(*) as total_positions,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_positions,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_positions
            FROM read_positions
        """)
        positions_stats = cursor.fetchone()
        
        print(f"\nREAD_POSITIONS:")
        print(f"  Total positions: {positions_stats[0]}")
        print(f"  Active positions (is_active=1): {positions_stats[1]}")
        print(f"  Inactive positions (is_active=0): {positions_stats[2]}")
        
        # Check deals with their positions status
        cursor.execute("""
            SELECT 
                d.deal_key,
                d.client_name,
                d.is_active as deal_active,
                COUNT(p.id) as total_positions,
                SUM(CASE WHEN p.is_active = 1 THEN 1 ELSE 0 END) as active_positions,
                SUM(CASE WHEN p.is_active = 0 THEN 1 ELSE 0 END) as inactive_positions
            FROM read_deals d
            LEFT JOIN read_positions p ON d.id = p.deal_id
            GROUP BY d.id, d.deal_key, d.client_name, d.is_active
            ORDER BY d.is_active DESC, total_positions DESC
            LIMIT 10
        """)
        sample_deals = cursor.fetchall()
        
        print(f"\n=== SAMPLE DEALS WITH POSITIONS STATUS ===")
        for deal_key, client_name, deal_active, total_pos, active_pos, inactive_pos in sample_deals:
            deal_status = "ACTIVE" if deal_active else "INACTIVE"
            print(f"Deal: {deal_key}")
            print(f"  Client: {client_name}")
            print(f"  Deal Status: {deal_status}")
            print(f"  Positions: {active_pos} active, {inactive_pos} inactive (total: {total_pos})")
            print()
        
        # Check if there are any inconsistencies
        cursor.execute("""
            SELECT 
                d.deal_key,
                d.is_active as deal_active,
                COUNT(p.id) as total_positions,
                SUM(CASE WHEN p.is_active = 1 THEN 1 ELSE 0 END) as active_positions
            FROM read_deals d
            LEFT JOIN read_positions p ON d.id = p.deal_id
            WHERE d.is_active = 0 AND p.is_active = 1
            GROUP BY d.id, d.deal_key, d.is_active
        """)
        inconsistent_deals = cursor.fetchall()
        
        if inconsistent_deals:
            print(f"\n⚠️  INCONSISTENCIES FOUND:")
            print(f"  Deals marked as inactive but have active positions:")
            for deal_key, deal_active, total_pos, active_pos in inconsistent_deals:
                print(f"    {deal_key}: {active_pos} active positions")
        else:
            print(f"\n✅ No inconsistencies found - all inactive deals have inactive positions")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking is_active status: {e}")

if __name__ == "__main__":
    check_is_active_status() 