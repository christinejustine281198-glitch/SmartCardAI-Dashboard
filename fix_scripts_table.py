import sqlite3
import os
import shutil

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")
BACKUP_FILE = os.path.join(os.path.dirname(__file__), "app_backup_before_fix.db")

# Backup current DB
if os.path.exists(DB_FILE):
    shutil.copy2(DB_FILE, BACKUP_FILE)
    print(f"Backup created: {BACKUP_FILE}")

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Required columns
required_cols = ['id','name','code','output','error','success_log','success_code','timestamp','run_type','user','status']

# Check existing columns
c.execute("PRAGMA table_info(scripts)")
existing_cols = [row[1] for row in c.fetchall()]

# Fix table if columns missing
if not all(col in existing_cols for col in required_cols):
    print("Fixing scripts table...")
    # Create new temp table with correct structure
    c.execute('''
    CREATE TABLE IF NOT EXISTS scripts_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        code TEXT,
        output TEXT,
        error TEXT,
        success_log TEXT,
        success_code TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        run_type TEXT,
        user TEXT,
        status TEXT DEFAULT "paused"
    )
    ''')
    # Copy existing data (only columns that exist)
    copy_cols = [col for col in required_cols if col in existing_cols]
    if copy_cols:
        cols_str = ",".join(copy_cols)
        c.execute(f"INSERT INTO scripts_new ({cols_str}) SELECT {cols_str} FROM scripts")
    # Replace old table
    c.execute("DROP TABLE IF EXISTS scripts")
    c.execute("ALTER TABLE scripts_new RENAME TO scripts")
    print("Scripts table fixed successfully.")
else:
    print("Scripts table already correct.")

conn.commit()
conn.close()
