import sqlite3, os

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")
print("Using DB at:", DB_FILE)

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Get table names
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in c.fetchall()]
print("Tables in DB:", tables)

# Get columns of scripts table
if "scripts" in tables:
    c.execute("PRAGMA table_info(scripts)")
    cols = [col[1] for col in c.fetchall()]
    print("Columns in 'scripts':", cols)
else:
    print("'scripts' table does not exist")

conn.close()
