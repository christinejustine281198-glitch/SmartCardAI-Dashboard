import sqlite3
import datetime

DB_FILE = "app.db"
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Helper: check if table exists
def table_exists(name):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return c.fetchone() is not None

if not table_exists("users"):
    print("Error: users table does not exist. Cannot migrate.")
else:
    # Backup existing users
    c.execute("SELECT id, username, password FROM users")
    users = c.fetchall()

    # Only rename if old table not already renamed
    if not table_exists("users_old"):
        c.execute("ALTER TABLE users RENAME TO users_old")
        print("Old users table renamed to users_old")
    else:
        print("users_old table already exists. Skipping rename.")

    # Create new users table
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
    print("New users table created")

    # Copy old data
    now = datetime.datetime.now().isoformat()
    for user in users:
        user_id, username, password = user
        c.execute('''
            INSERT OR IGNORE INTO users (username, password, terms_accepted_at, privacy_accepted_at)
            VALUES (?, ?, ?, ?)
        ''', (username, password, now, now))
    print("Old users migrated")

    # Drop old table
    if table_exists("users_old"):
        c.execute("DROP TABLE users_old")
        print("Old users_old table dropped")

conn.commit()
conn.close()
print("Migration complete")
