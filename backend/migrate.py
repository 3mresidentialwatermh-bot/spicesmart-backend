"""
migrate.py — Add new columns to users table without destroying data.
Run once: python migrate.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'spicesapp.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Get existing columns
    cur.execute("PRAGMA table_info(users)")
    existing = {row[1] for row in cur.fetchall()}
    print(f"Existing columns: {existing}")

    new_columns = {
        'city':    'VARCHAR(100)',
        'state':   'VARCHAR(100)',
        'pincode': 'VARCHAR(10)',
        'gstin':   'VARCHAR(20)',
    }

    for col, col_type in new_columns.items():
        if col not in existing:
            print(f"  Adding column: {col} {col_type}")
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        else:
            print(f"  Column already exists: {col}")

    # Also add payment_id to orders if missing
    cur.execute("PRAGMA table_info(orders)")
    order_cols = {row[1] for row in cur.fetchall()}
    if 'payment_id' not in order_cols and 'payment_ref' not in order_cols:
        print("  Adding column: payment_id VARCHAR(100) to orders")
        cur.execute("ALTER TABLE orders ADD COLUMN payment_id VARCHAR(100)")

    conn.commit()
    conn.close()
    print("\nMigration complete!")

if __name__ == '__main__':
    migrate()
