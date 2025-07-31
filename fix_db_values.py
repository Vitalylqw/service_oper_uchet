import sqlite3
import sys
import time

def fix_database_values():
    """Fix database values by converting Status.* to lowercase values."""
    
    db_path = 'data/service_oper_uchet.sqlite'
    print(f"Connecting to {db_path}")
    
    # Try multiple times with timeout
    for attempt in range(3):
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Check current values
            print(f"\n=== Attempt {attempt + 1} ===")
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
            conn.close()
            return
            
        except sqlite3.OperationalError as e:
            print(f"❌ Database locked on attempt {attempt + 1}: {e}")
            if attempt < 2:
                print("Waiting 5 seconds before retry...")
                time.sleep(5)
            else:
                print("Failed after 3 attempts")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        finally:
            try:
                conn.close()
            except:
                pass

if __name__ == "__main__":
    fix_database_values() 