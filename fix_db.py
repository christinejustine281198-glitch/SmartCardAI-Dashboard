import sqlite3
import os
import shutil
import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")
BACKUP_FILE = os.path.join(os.path.dirname(__file__), "app_backup.db")

# 1️⃣ Backup existing DB
if os.path.exists(DB_FILE):
    shutil.copy2(DB_FILE, BACKUP_FILE)
    print(f"Backup created: {BACKUP_FILE}")

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 2️⃣ Ensure users table exists
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT,
    reset_token TEXT,
    terms_accepted_at DATETIME,
    privacy_accepted_at DATETIME
)
''')
print("Users table verified/created.")

# 3️⃣ Ensure scripts table exists
c.execute('''
CREATE TABLE IF NOT EXISTS scripts (
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
print("Scripts table verified/created.")

# 4️⃣ Ensure columns exist
c.execute("PRAGMA table_info(scripts)")
existing_cols = [col[1] for col in c.fetchall()]

required_cols = ["success_log", "success_code"]
for col in required_cols:
    if col not in existing_cols:
        print(f"Adding missing column: {col}")
        c.execute(f"ALTER TABLE scripts ADD COLUMN {col} TEXT")

conn.commit()
conn.close()
print("Database columns verified and updated successfully.")
