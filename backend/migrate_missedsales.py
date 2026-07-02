import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'spicesapp.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Creating missed_sales table...")
    cur.execute('''
        CREATE TABLE IF NOT EXISTS missed_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount NUMERIC(12, 2) DEFAULT 0,
            reason VARCHAR(200),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Migration complete. Created missed_sales table.")

if __name__ == '__main__':
    migrate()
