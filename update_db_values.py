import sqlite3
import sys

def update_database_values():
    """Update database values by converting Status.* to lowercase values."""
    
    db_path = 'data/service_oper_uchet.sqlite'
    print(f"Connecting to {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current values
        print("\n=== Current values ===")
        cursor.execute("SELECT DISTINCT is_paid, COUNT(*) FROM read_deals GROUP BY is_paid")
        print("is_paid values:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
        cursor.execute("SELECT DISTINCT is_shipped, COUNT(*) FROM read_deals GROUP BY is_shipped")
        print("\nis_shipped values:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        # Update values
        print("\n=== Updating values ===")
        
        # Update is_paid
        cursor.execute("""
            UPDATE read_deals 
            SET is_paid = CASE 
                WHEN is_paid = 'Status.COMPLETED' THEN 'completed'
                WHEN is_paid = 'Status.PAID' THEN 'paid'
                WHEN is_paid = 'Status.PARTIAL' THEN 'partial'
                WHEN is_paid = 'Status.PENDING' THEN 'pending'
                ELSE is_paid
            END
        """)
        print(f"Updated {cursor.rowcount} is_paid records")
        
        # Update is_shipped
        cursor.execute("""
            UPDATE read_deals 
            SET is_shipped = CASE 
                WHEN is_shipped = 'Status.COMPLETED' THEN 'completed'
                WHEN is_shipped = 'Status.SHIPPED' THEN 'shipped'
                WHEN is_shipped = 'Status.PARTIAL' THEN 'partial'
                WHEN is_shipped = 'Status.PENDING' THEN 'pending'
                ELSE is_shipped
            END
        """)
        print(f"Updated {cursor.rowcount} is_shipped records")
        
        # Commit changes
        conn.commit()
        
        # Check updated values
        print("\n=== Updated values ===")
        cursor.execute("SELECT DISTINCT is_paid, COUNT(*) FROM read_deals GROUP BY is_paid")
        print("is_paid values:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
        cursor.execute("SELECT DISTINCT is_shipped, COUNT(*) FROM read_deals GROUP BY is_shipped")
        print("\nis_shipped values:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
        print("\n✅ Database values updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    update_database_values() 