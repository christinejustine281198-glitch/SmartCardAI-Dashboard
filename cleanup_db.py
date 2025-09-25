import os
import sqlite3
import shutil

# Path to your DB
DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")

# 1️⃣ Delete __pycache__ folders
for root, dirs, files in os.walk(os.path.dirname(__file__)):
    for d in dirs:
        if d == "__pycache__":
            cache_path = os.path.join(root, d)
            shutil.rmtree(cache_path)
            print(f"Deleted cache: {cache_path}")

# 2️⃣ Backup the current DB
backup_file = DB_FILE.replace(".db", "_backup.db")
if os.path.exists(DB_FILE):
    shutil.copy2(DB_FILE, backup_file)
    print(f"Backup created: {backup_file}")

# 3️⃣ Validate and fix 'scripts' table columns
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

c.execute("PRAGMA table_info(scripts)")
existing_cols = [col[1] for col in c.fetchall()]
required_cols = ['id','name','code','output','error','timestamp','run_type','user','status','success_log','success_code']

for col in required_cols:
    if col not in existing_cols:
        if col in ['success_log','success_code']:
            print(f"Adding missing column: {col}")
            c.execute(f"ALTER TABLE scripts ADD COLUMN {col} TEXT")
        else:
            print(f"Warning: column '{col}' is missing but cannot be auto-added.")

conn.commit()
conn.close()
print("DB cleanup and validation complete.")
