from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, subprocess, json, os, secrets, smtplib, datetime
from email.message import EmailMessage
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash, check_password_hash

# --- Config ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey")
DB_FILE = "app.db"

# SMTP credentials (Jude-provided)
SMTP_SERVER = "mail.smartcardai.com"
SMTP_PORT = 587
SMTP_USER = "support@smartcardai.com"
SMTP_PASS = "Smart@Mail2025!"  # ensure exact casing

# --- DB init ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE,
                    password TEXT,
                    reset_token TEXT,
                    terms_accepted_at DATETIME,
                    privacy_accepted_at DATETIME
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS scripts (
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
                )''')
    conn.commit()
    conn.close()

init_db()

# --- Scheduler ---
scheduler = BackgroundScheduler()
scheduler.start()

# --- Helpers ---
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, args)
    rv = c.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def send_reset_email(to_email, token):
    try:
        msg = EmailMessage()
        msg['Subject'] = "Password Reset Link"
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        reset_link = f"http://127.0.0.1:5000/reset_password/{token}"
        msg.set_content(f"Click this link to reset your password: {reset_link}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)

def run_node_runner(code):
    """
    Run runner.js as before — returns (stdout, stderr)
    """
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

# --- Script Runner used by scheduler ---
def run_scheduled_script(script_id):
    row = query_db("SELECT name, code, user FROM scripts WHERE id=?", (script_id,), one=True)
    if not row:
        return
    name, code, user = row[0], row[1], row[2]
    output, error = "", ""
    success_log, success_code = "", ""
    stdout, stderr = run_node_runner(code)
    # attempt to parse JSON stdout
    try:
        data = json.loads(stdout) if stdout else {}
        logs = "\n".join(data.get("logs", [])) if isinstance(data, dict) else ""
        final = str(data.get("result", "")) if isinstance(data, dict) else ""
        output = logs + ("\n" + final if final else "")
        if not stderr:
            success_log = "Script executed successfully"
            success_code = "200"
    except Exception:
        # fallback
        output = stdout
        error = stderr
    store_script_record(name + " (scheduled)", code, output, error, success_log, success_code, "cron", user, "running")

# --- Routes ---

@app.route("/")
def home():
    return redirect(url_for("history")) if "user" in session else redirect(url_for("login"))

# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not (username and email and password):
            flash("Please fill all required fields", "danger")
            return render_template("signup.html")
        # check checkboxes
        terms = request.form.get("terms")
        privacy = request.form.get("privacy")
        if not terms or not privacy:
            flash("You must accept Terms & Privacy", "danger")
            return render_template("signup.html")
        terms_time = datetime.datetime.now().isoformat()
        privacy_time = terms_time
        hashed = generate_password_hash(password)
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO users (username,email,password,terms_accepted_at,privacy_accepted_at) VALUES (?,?,?,?,?)",
                      (username, email, hashed, terms_time, privacy_time))
            conn.commit()
            conn.close()
            flash("Signup successful. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists", "danger")
            return render_template("signup.html")
    return render_template("signup.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        # try username first, then email
        row = query_db("SELECT username, password FROM users WHERE username=? COLLATE NOCASE", (identifier,), one=True)
        if not row:
            row = query_db("SELECT username, password FROM users WHERE email=? COLLATE NOCASE", (identifier.lower(),), one=True)
        if not row:
            flash("Invalid credentials", "danger")
            return render_template("login.html")
        db_username, db_hashed = row[0], row[1]
        if check_password_hash(db_hashed, password):
            session["user"] = db_username
            flash("Logged in", "success")
            return redirect(url_for("history"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out", "info")
    return redirect(url_for("login"))

# Forgot password
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Enter your email", "danger")
            return render_template("forgot_password.html")
        token = secrets.token_urlsafe(24)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE users SET reset_token=? WHERE email=?", (token, email))
        conn.commit()
        conn.close()
        ok, err = send_reset_email(email, token)
        if ok:
            flash("Reset link sent to your email (check spam if not visible).", "success")
        else:
            flash(f"Failed to send email: {err}", "danger")
        return render_template("forgot_password.html")
    return render_template("forgot_password.html")

# Reset password
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        if not password or password != password2:
            flash("Passwords must match", "danger")
            return render_template("reset_password.html", token=token)
        hashed = generate_password_hash(password)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE users SET password=?, reset_token=NULL WHERE reset_token=?", (hashed, token))
        conn.commit()
        conn.close()
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", token=token)

# Run script (create)
@app.route("/run_script", methods=["GET", "POST"])
def run_script():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        script_name = request.form.get("script_name", "").strip()
        code = request.form.get("code", "")
        run_type = request.form.get("run_type", "manual")
        if not script_name or not code:
            flash("Script name and code are required", "danger")
            return render_template("run_script.html", script_name=script_name, code=code, run_type=run_type)
        # execute immediately (manual)
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
        store_script_record(script_name, code, output, error, success_log, success_code, run_type, session["user"], "paused")
        flash("Script saved.", "success")
        return redirect(url_for("history"))
    return render_template("run_script.html")

# History
@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))
    scripts = query_db("SELECT id,name,timestamp,run_type,status FROM scripts WHERE user=? ORDER BY id DESC", (session["user"],))
    return render_template("history.html", scripts=scripts)

# Script operations
@app.route("/delete/<int:script_id>")
def delete_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    query_db("DELETE FROM scripts WHERE id=? AND user=?", (script_id, session["user"]))
    flash("Script deleted.", "info")
    return redirect(url_for("history"))

@app.route("/start/<int:script_id>")
def start_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    # avoid duplicate job for same script id
    job_id = f"script_{script_id}"
    existing = scheduler.get_job(job_id)
    if existing is None:
        scheduler.add_job(run_scheduled_script, "interval", minutes=1, args=[script_id], id=job_id, replace_existing=True)
    query_db("UPDATE scripts SET status=? WHERE id=? AND user=?", ("running", script_id, session["user"]))
    flash("Script scheduled (1 min interval).", "success")
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
    flash("Script paused.", "info")
    return redirect(url_for("history"))

@app.route("/edit/<int:script_id>", methods=["GET", "POST"])
def edit_script(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("script_name", "").strip()
        code = request.form.get("code", "")
        query_db("UPDATE scripts SET name=?, code=? WHERE id=? AND user=?", (name, code, script_id, session["user"]))
        flash("Script updated.", "success")
        return redirect(url_for("history"))
    row = query_db("SELECT name, code FROM scripts WHERE id=? AND user=?", (script_id, session["user"]), one=True)
    if row:
        return render_template("run_script.html", script_name=row[0], code=row[1])
    flash("Script not found.", "danger")
    return redirect(url_for("history"))

# Logs endpoint
@app.route("/logs/<int:script_id>")
def get_logs(script_id):
    if "user" not in session:
        return redirect(url_for("login"))
    log_type = request.args.get("type", "output")  # output, error, success_log
    # sanitize column name
    if log_type not in ("output", "error", "success_log", "success_code"):
        log_type = "output"
    rows = query_db(f"SELECT {log_type}, timestamp FROM scripts WHERE id=? AND user=?", (script_id, session["user"]))
    # return tuples (log, timestamp)
    return jsonify([(row[0] if row[0] is not None else "", row[1]) for row in rows])

# Run
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render gives PORT
    app.run(host="0.0.0.0", port=port, debug=True)

