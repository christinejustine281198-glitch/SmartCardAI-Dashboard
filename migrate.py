import sqlite3

DB_FILE = "app.db"

def migrate_scripts_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Check existing columns
    c.execute("PRAGMA table_info(scripts)")
    existing_cols = [col[1] for col in c.fetchall()]
    print("Existing columns:", existing_cols)

    # Add missing columns
    if "success_log" not in existing_cols:
        print("Adding column: success_log")
        c.execute("ALTER TABLE scripts ADD COLUMN success_log TEXT")
    if "success_code" not in existing_cols:
        print("Adding column: success_code")
        c.execute("ALTER TABLE scripts ADD COLUMN success_code TEXT")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate_scripts_table()


