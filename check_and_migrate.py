import sqlite3, os

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")
print("Using DB at:", DB_FILE)

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Check tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print("Tables in DB:", tables)

# Check columns in 'scripts'
c.execute("PRAGMA table_info(scripts)")
cols = [col[1] for col in c.fetchall()]
print("Columns in 'scripts':", cols)

# Add missing columns
if 'success_log' not in cols:
    print("Adding column: success_log")
    c.execute("ALTER TABLE scripts ADD COLUMN success_log TEXT")
if 'success_code' not in cols:
    print("Adding column: success_code")
    c.execute("ALTER TABLE scripts ADD COLUMN success_code TEXT")

conn.commit()
conn.close()
print("Migration completed successfully.")
