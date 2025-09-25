import sqlite3, os, shutil, datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")
BACKUP_FILE = os.path.join(os.path.dirname(__file__), "app_backup.db")

# 1️⃣ Backup current DB
if os.path.exists(DB_FILE):
    shutil.copy2(DB_FILE, BACKUP_FILE)
    print(f"Backup created: {BACKUP_FILE}")

# 2️⃣ Connect and create new DB
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 3️⃣ Users table
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

# 4️⃣ Scripts table
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

# 5️⃣ Optional: migrate existing users
# Check if backup exists
if os.path.exists(BACKUP_FILE):
    backup_conn = sqlite3.connect(BACKUP_FILE)
    bc = backup_conn.cursor()
    bc.execute("SELECT username, email, password FROM users")
    users = bc.fetchall()
    now = datetime.datetime.now().isoformat()
    for u in users:
        username, email, password = u
        c.execute('''
            INSERT OR IGNORE INTO users (username, email, password, terms_accepted_at, privacy_accepted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email if email else "", password, now, now))
    backup_conn.close()
    print("Existing users migrated from backup")

conn.commit()
conn.close()
print("New DB created successfully with correct tables and columns.")
