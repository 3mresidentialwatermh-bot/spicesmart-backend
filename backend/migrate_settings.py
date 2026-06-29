import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'spicesapp.db')

def migrate():
    print(f"Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            brand_name VARCHAR(100),
            brand_logo_url VARCHAR(500),
            razorpay_key_id VARCHAR(100),
            razorpay_key_secret VARCHAR(100)
        )
    ''')
    
    # Check if empty, insert default row
    c.execute('SELECT COUNT(*) FROM settings')
    count = c.fetchone()[0]
    
    if count == 0:
        print("Inserting default settings row...")
        c.execute('''
            INSERT INTO settings (id, brand_name, razorpay_key_id, razorpay_key_secret) 
            VALUES (1, 'SpicesMart', '', '')
        ''')
    
    conn.commit()
    conn.close()
    print("Settings migration complete.")

if __name__ == '__main__':
    migrate()
