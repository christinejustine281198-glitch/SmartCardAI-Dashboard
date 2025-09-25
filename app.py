from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3, os, secrets, subprocess, json, datetime, shutil

app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------- DATABASE CONFIG --------------------
DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")
BACKUP_FILE = os.path.join(os.path.dirname(__file__), "app_backup.db")
print("Using DB at:", DB_FILE)

# -------------------- DB FIX ROUTINE --------------------
def ensure_scripts_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    required_cols = ['id','name','code','output','error','success_log','success_code','timestamp','run_type','user','status']

    # Get existing columns
    c.execute("PRAGMA table_info(scripts)")
    existing_cols = [row[1] for row in c.fetchall()]

    # If table missing columns, rebuild table
    if not all(col in existing_cols for col in required_cols):
        print("Fixing scripts table...")
        # Create temporary new table
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
        # Copy existing data
        copy_cols = [col for col in required_cols if col in existing_cols]
        if copy_cols:
            cols_str = ",".join(copy_cols)
            c.execute(f"INSERT INTO scripts_new ({cols_str}) SELECT {cols_str} FROM scripts")
        # Replace old table
        c.execute("DROP TABLE IF EXISTS scripts")
        c.execute("ALTER TABLE scripts_new RENAME TO scripts")
        print("Scripts table fixed successfully.")

    conn.commit()
    conn.close()

# -------------------- DB INIT & MIGRATION --------------------
def init_db():
    # Backup existing DB
    if os.path.exists(DB_FILE):
        shutil.copy2(DB_FILE, BACKUP_FILE)
        print(f"Backup created: {BACKUP_FILE}")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Users table
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

    # Ensure scripts table exists with correct columns
    ensure_scripts_table()

    # Create default admin if not exists
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        hashed = generate_password_hash("admin123")
        now = datetime.datetime.now().isoformat()
        c.execute("INSERT INTO users (username,email,password,terms_accepted_at,privacy_accepted_at) VALUES (?,?,?,?,?)",
                  ("admin", "admin@example.com", hashed, now, now))
        print("Default admin user created: username=admin, password=admin123")

    # Add sample script if scripts table empty
    c.execute("SELECT COUNT(*) FROM scripts")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO scripts (name, code, output, error, success_log, success_code, run_type, user, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ("Hello World", 'console.log("Hello World")', "", "", "", "", "manual", "admin", "paused"))
        print("Sample script added")

    conn.commit()
    conn.close()
    print("DB initialized and migration complete.")

# Initialize DB
init_db()

# -------------------- SCHEDULER --------------------
scheduler = BackgroundScheduler()
scheduler.start()

# -------------------- HELPERS --------------------
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, args)
    rv = c.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def run_node_runner(code):
    try:
        runner_path = os.path.join(os.path.dirname(__file__), "runner.js")
        result = subprocess.run(["node", runner_path, code], capture_output=True, text=True, timeout=60)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)

def store_script_record(name, code, output, error, success_log, success_code, run_type, user, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO scripts (name, code, output, error, success_log, success_code, run_type, user, status) VALUES (?,?,?,?,?,?,?,?,?)",
        (name, code, output, error, success_log, success_code, run_type, user, status)
    )
    conn.commit()
    conn.close()

def run_scheduled_script(script_id):
    row = query_db("SELECT name, code, user FROM scripts WHERE id=?", (script_id,), one=True)
    if not row:
        return
    name, code, user = row
    output, error, success_log, success_code = "", "", "", ""
    stdout, stderr = run_node_runner(code)
    try:
        data = json.loads(stdout) if stdout else {}
        logs = "\n".join(data.get("logs", [])) if isinstance(data, dict) else ""
        final = str(data.get("result", "")) if isinstance(data, dict) else ""
        output = logs + ("\n" + final if final else "")
        if not stderr:
            success_log = "Script executed successfully"
            success_code = "200"
    except Exception:
        output = stdout
        error = stderr
    store_script_record(name + " (scheduled)", code, output, error, success_log, success_code, "cron", user, "running")

# -------------------- ROUTES --------------------
@app.route("/")
def home():
    return redirect(url_for("history")) if "user" in session else redirect(url_for("login"))

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        terms = request.form.get("terms")
        privacy = request.form.get("privacy")
        if not (username and email and password and terms and privacy):
            flash("Fill all fields and accept Terms & Privacy", "danger")
            return render_template("signup.html")
        hashed = generate_password_hash(password)
        now = datetime.datetime.now().isoformat()
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO users (username,email,password,terms_accepted_at,privacy_accepted_at) VALUES (?,?,?,?,?)",
                      (username, email, hashed, now, now))
            conn.commit()
            conn.close()
            flash("Signup successful. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists", "danger")
            return render_template("signup.html")
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username","").strip()
        password = request.form.get("password","")
        row = query_db("SELECT username,password FROM users WHERE username=? COLLATE NOCASE", (identifier,), one=True)
        if not row:
            row = query_db("SELECT username,password FROM users WHERE email=? COLLATE NOCASE", (identifier.lower(),), one=True)
        if not row:
            flash("Invalid credentials", "danger")
            return render_template("login.html")
        db_username, db_hashed = row
        if check_password_hash(db_hashed, password):
            session["user"] = db_username
            flash("Logged in", "success")
            return redirect(url_for("history"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/forgot_password", methods=["GET","POST"])
def forgot_password():
    if request.method=="POST":
        email = request.form.get("email","").strip().lower()
        if not email:
            flash("Enter your email", "danger")
            return render_template("forgot_password.html")
        token = secrets.token_urlsafe(6)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE users SET reset_token=? WHERE email=?", (token,email))
        conn.commit()
        conn.close()
        print(f"[RESET TOKEN] {token}")  # Simulate sending token via email
        flash("Reset token generated. Check console.", "info")
    return render_template("forgot_password.html")

@app.route("/reset_password", methods=["GET","POST"])
def reset_password():
    if request.method=="POST":
        token = request.form.get("token","")
        password = request.form.get("password","")
        password2 = request.form.get("password2","")
        if password != password2:
            flash("Passwords must match", "danger")
            return render_template("reset_password.html")
        row = query_db("SELECT username FROM users WHERE reset_token=?", (token,), one=True)
        if row:
            username = row[0]
            hashed = generate_password_hash(password)
            query_db("UPDATE users SET password=?, reset_token=NULL WHERE username=?", (hashed, username))
            flash("Password reset successful. Login now.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid reset token", "danger")
    return render_template("reset_password.html")

@app.route("/run_script", methods=["GET","POST"])
def run_script():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method=="POST":
        script_name = request.form.get("script_name","").strip()
        code = request.form.get("code","")
        run_type = request.form.get("run_type","manual")
        if not script_name or not code:
            flash("Script name and code are required", "danger")
            return render_template("run_script.html")
        output,error,success_log,success_code = "","","",""
        stdout, stderr = run_node_runner(code)
        try:
            data = json.loads(stdout) if stdout else {}
            logs = "\n".join(data.get("logs",[])) if isinstance(data,dict) else ""
            final = str(data.get("result","")) if isinstance(data,dict) else ""
            output = logs + ("\n"+final if final else "")
            if not stderr:
                success_log = "Script executed successfully"
                success_code = "200"
        except Exception:
            output = stdout
            error = stderr
        store_script_record(script_name, code, output, error, success_log, success_code, run_type, session["user"], "paused")
        flash("Script saved", "success")
        return redirect(url_for("history"))
    return render_template("run_script.html")

@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))
    scripts = query_db("SELECT id,name,timestamp,run_type,status FROM scripts WHERE user=? ORDER BY id DESC", (session["user"],))
    return render_template("history.html", scripts=scripts)

@app.route("/delete/<int:script_id>")
def delete_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    query_db("DELETE FROM scripts WHERE id=? AND user=?", (script_id, session["user"]))
    flash("Script deleted", "info")
    return redirect(url_for("history"))

@app.route("/edit/<int:script_id>", methods=["GET","POST"])
def edit_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    script = query_db("SELECT id,name,code FROM scripts WHERE id=? AND user=?", (script_id, session["user"]), one=True)
    if not script:
        flash("Script not found", "danger")
        return redirect(url_for("history"))
    if request.method=="POST":
        name = request.form.get("script_name","").strip()
        code = request.form.get("code","")
        if not name or not code:
            flash("Name and code required", "danger")
            return render_template("edit_script.html", script=script)
        query_db("UPDATE scripts SET name=?, code=? WHERE id=? AND user=?", (name, code, script_id, session["user"]))
        flash("Script updated", "success")
        return redirect(url_for("history"))
    return render_template("edit_script.html", script=script)

@app.route("/start/<int:script_id>")
def start_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    job_id = f"script_{script_id}"
    if not scheduler.get_job(job_id):
        scheduler.add_job(run_scheduled_script, "interval", minutes=1, args=[script_id], id=job_id, replace_existing=True)
    query_db("UPDATE scripts SET status=? WHERE id=? AND user=?", ("running", script_id, session["user"]))
    flash("Script scheduled", "success")
    return redirect(url_for("history"))

@app.route("/pause/<int:script_id>")
def pause_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    job_id = f"script_{script_id}"
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)
    query_db("UPDATE scripts SET status=? WHERE id=? AND user=?", ("paused", script_id, session["user"]))
    flash("Script paused", "info")
    return redirect(url_for("history"))

@app.route("/logs/<int:script_id>")
def get_logs(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    log_type = request.args.get("type","output")
    if log_type not in ("output","error","success_log","success_code"):
        log_type = "output"
    rows = query_db(f"SELECT {log_type},timestamp FROM scripts WHERE id=? AND user=?", (script_id, session["user"]))
    return jsonify([(row[0] if row[0] else "", row[1]) for row in rows])

# -------------------- RUN APP --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)

