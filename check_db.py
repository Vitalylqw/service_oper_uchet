import sqlite3

conn = sqlite3.connect('data/service_oper_uchet.sqlite')
cursor = conn.cursor()

print("=== Database Status ===")
print("Table structure:")
cursor.execute("PRAGMA table_info(read_deals)")
for row in cursor.fetchall():
    if 'is_paid' in row[1] or 'is_shipped' in row[1]:
        print(f"  {row[1]} {row[2]}")

print("\nValues in is_paid:")
cursor.execute("SELECT DISTINCT is_paid, COUNT(*) FROM read_deals GROUP BY is_paid")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\nValues in is_shipped:")
cursor.execute("SELECT DISTINCT is_shipped, COUNT(*) FROM read_deals GROUP BY is_shipped")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close() 