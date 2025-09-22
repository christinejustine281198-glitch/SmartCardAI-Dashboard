import sqlite3

DB_FILE = "app.db"

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Drop old table
c.execute("DROP TABLE IF EXISTS scripts")
conn.commit()
conn.close()

print("✅ scripts table dropped. Next time you run app.py it will recreate the table with 'user' column.")
