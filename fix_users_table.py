import sqlite3

DB_FILE = "app.db"

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Add email column if it doesn't exist
try:
    c.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
except sqlite3.OperationalError:
    print("Email column already exists")

# Add reset_token column if it doesn't exist
try:
    c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
except sqlite3.OperationalError:
    print("reset_token column already exists")

conn.commit()
conn.close()
print("Columns added successfully")
