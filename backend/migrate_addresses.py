import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'spicesapp.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create addresses table
    print("Creating addresses table...")
    cur.execute('''
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title VARCHAR(50),
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            pincode VARCHAR(10),
            is_default BOOLEAN DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Get existing columns in orders table
    cur.execute("PRAGMA table_info(orders)")
    existing = {row[1] for row in cur.fetchall()}
    print(f"Existing columns in orders: {existing}")

    new_columns = {
        'shipping_address': 'TEXT',
        'shipping_city': 'VARCHAR(100)',
        'shipping_state': 'VARCHAR(100)',
        'shipping_pincode': 'VARCHAR(10)',
    }

    added = 0
    for col, dtype in new_columns.items():
        if col not in existing:
            print(f"Adding column '{col}' to 'orders' table...")
            cur.execute(f"ALTER TABLE orders ADD COLUMN {col} {dtype}")
            added += 1

    conn.commit()
    conn.close()
    print(f"Migration complete. Added {added} columns.")

if __name__ == '__main__':
    migrate()
