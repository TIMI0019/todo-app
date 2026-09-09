from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
import re
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-key")
app.permanent_session_lifetime = datetime.timedelta(days=30)

# Environment variables for database and Gmail SMTP
DATABASE_URL = os.environ.get("DATABASE_URL")
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

DB_FILE = "todo.db"


# --- Helper Functions ---
def send_otp_email(to_email, otp):
    """Sends an OTP email using Gmail SMTP over SSL (Port 465)."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("--- [LOG] WARNING: MAIL_USERNAME or MAIL_PASSWORD environment variables not set! ---", flush=True)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Doneify Password Reset Code"
    msg["From"] = f"Doneify <{MAIL_USERNAME}>"
    msg["To"] = to_email

    html_content = f"""
        <h3>Password Reset Request</h3>
        <p>Your 6-digit verification code is: <strong style="font-size: 20px;">{otp}</strong></p>
        <p>This code will expire in 10 minutes.</p>
    """
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Use Port 465 (SSL) with a 10-second timeout to avoid worker timeouts
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_USERNAME, [to_email], msg.as_string())
        print(f"--- [LOG] Gmail SMTP Success! Email sent to: {to_email} ---", flush=True)
        return True
    except Exception as e:
        print(f"--- [LOG] Gmail SMTP Error: {e} ---", flush=True)
        return False


def is_password_strong(password):
    """At least 8 chars, one uppercase, one lowercase, one digit, one special character."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def get_db():
    if DATABASE_URL:
        # PostgreSQL for Render production
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        # SQLite for local development
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    if DATABASE_URL:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(50),
                otp VARCHAR(10),
                otp_expiry VARCHAR(100)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                description TEXT NOT NULL,
                done INTEGER NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255) NOT NULL,
                content TEXT,
                date VARCHAR(50),
                time VARCHAR(50)
            );
        """)
        conn.commit()
        conn.close()
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        columns_to_add = [
            ("email", "TEXT"),
            ("phone", "TEXT"),
            ("otp", "TEXT"),
            ("otp_expiry", "TEXT")
        ]
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                done INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                date TEXT,
                time TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
        conn.close()


init_db()


def login_required_json():
    """Returns True if the request should be blocked (no logged-in user)."""
    return "user_id" not in session


# ---------- Auth Routes ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            return render_template("signup.html", error="Username, email, and password are required.")

        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match.")

        if not is_password_strong(password):
            return render_template("signup.html", error="Password must be at least 8 characters and include an uppercase letter, a lowercase letter, a number, and a special character.")

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            if DATABASE_URL:
                cursor.execute(
                    "INSERT INTO users (username, password, email, phone) VALUES (%s, %s, %s, %s) RETURNING id",
                    (username, hashed_password, email, phone)
                )
                new_user_id = cursor.fetchone()["id"]
            else:
                cursor.execute(
                    "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
                    (username, hashed_password, email, phone)
                )
                new_user_id = cursor.lastrowid
            conn.commit()
        except Exception:
            conn.close()
            return render_template("signup.html", error="That username is already taken.")

        conn.close()

        session["user_id"] = new_user_id
        session["username"] = username
        return redirect(url_for("home"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me")

        conn = get_db()
        cursor = conn.cursor()
        
        query = "SELECT * FROM users WHERE username = %s" if DATABASE_URL else "SELECT * FROM users WHERE username = ?"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password"], password):
            return render_template("login.html", error="Incorrect username or password.")

        session.permanent = bool(remember_me)
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    return render_template("forgot_password.html", step="request")


@app.route("/request-otp", methods=["POST"])
def request_otp():
    email = request.form.get("email", "").strip()
    print(f"\n--- [LOG] Reset request received for email: '{email}' ---", flush=True)

    if not email:
        return render_template("forgot_password.html", step="request", error="Email is required.")

    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM users WHERE email = %s" if DATABASE_URL else "SELECT * FROM users WHERE email = ?"
    cursor.execute(query, (email,))
    user = cursor.fetchone()

    if not user:
        print(f"--- [LOG] DB Check: No account found matching email '{email}' ---", flush=True)
    else:
        print(f"--- [LOG] DB Check: Found user '{user['username']}' (ID: {user['id']}) ---", flush=True)
        
        otp = f"{secrets.randbelow(1000000):06d}"
        expiry = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()

        update_query = "UPDATE users SET otp = %s, otp_expiry = %s WHERE id = %s" if DATABASE_URL else "UPDATE users SET otp = ?, otp_expiry = ? WHERE id = ?"
        cursor.execute(update_query, (otp, expiry, user["id"]))
        conn.commit()
        print(f"--- [LOG] Generated OTP: {otp} | Expiry: {expiry} ---", flush=True)

        # Send via Gmail SMTP (SSL Port 465)
        send_otp_email(email, otp)

    conn.close()
    return render_template("forgot_password.html", step="verify", email=email)


@app.route("/verify-reset", methods=["POST"])
def verify_otp_and_reset():
    email = request.form.get("email", "").strip()
    otp = request.form.get("otp", "").strip()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    print(f"\n--- [LOG] OTP Verification attempt for email: '{email}' | Entered OTP: '{otp}' ---", flush=True)

    if new_password != confirm_password:
        return render_template("forgot_password.html", step="verify", email=email, error="Passwords do not match.")

    if not is_password_strong(new_password):
        return render_template("forgot_password.html", step="verify", email=email, error="Password must be at least 8 characters and include uppercase, lowercase, a number, and a special character.")

    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM users WHERE email = %s" if DATABASE_URL else "SELECT * FROM users WHERE email = ?"
    cursor.execute(query, (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        print("--- [LOG] Verification failed: User not found ---", flush=True)
        return render_template("forgot_password.html", step="verify", email=email, error="Invalid OTP code.")

    if not user["otp"] or user["otp"] != otp or not user["otp_expiry"]:
        conn.close()
        print("--- [LOG] Verification failed: Invalid or mismatched OTP ---", flush=True)
        return render_template("forgot_password.html", step="verify", email=email, error="Invalid OTP code.")

    expiry_time = datetime.datetime.fromisoformat(user["otp_expiry"])
    if datetime.datetime.now() > expiry_time:
        conn.close()
        print("--- [LOG] Verification failed: OTP expired ---", flush=True)
        return render_template("forgot_password.html", step="verify", email=email, error="OTP code has expired. Please request a new one.")

    hashed_password = generate_password_hash(new_password)
    update_query = "UPDATE users SET password = %s, otp = NULL, otp_expiry = NULL WHERE id = %s" if DATABASE_URL else "UPDATE users SET password = ?, otp = NULL, otp_expiry = NULL WHERE id = ?"
    cursor.execute(update_query, (hashed_password, user["id"]))
    conn.commit()
    conn.close()

    print("--- [LOG] Password updated successfully! Redirecting to login. ---", flush=True)
    flash("Password reset successfully. You can log in now.", "success")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session["username"])


# ---------- Task Routes ----------

@app.route("/api/tasks")
def get_tasks():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM tasks WHERE user_id = %s" if DATABASE_URL else "SELECT * FROM tasks WHERE user_id = ?"
    cursor.execute(query, (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    tasks_data = [{"id": r["id"], "description": r["description"], "done": bool(r["done"])} for r in rows]
    return jsonify(tasks_data)


@app.route("/api/tasks/add", methods=["POST"])
def add_task():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    description = data.get("description", "").strip()

    if description:
        conn = get_db()
        cursor = conn.cursor()
        query = "INSERT INTO tasks (user_id, description, done) VALUES (%s, %s, 0)" if DATABASE_URL else "INSERT INTO tasks (user_id, description, done) VALUES (?, ?, 0)"
        cursor.execute(query, (session["user_id"], description))
        conn.commit()
        conn.close()

    return get_tasks()


@app.route("/api/tasks/toggle", methods=["POST"])
def toggle_task():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    task_id = data.get("id")

    conn = get_db()
    cursor = conn.cursor()
    sel_query = "SELECT done FROM tasks WHERE id = %s AND user_id = %s" if DATABASE_URL else "SELECT done FROM tasks WHERE id = ? AND user_id = ?"
    cursor.execute(sel_query, (task_id, session["user_id"]))
    row = cursor.fetchone()
    if row is not None:
        new_done = 0 if row["done"] else 1
        upd_query = "UPDATE tasks SET done = %s WHERE id = %s AND user_id = %s" if DATABASE_URL else "UPDATE tasks SET done = ? WHERE id = ? AND user_id = ?"
        cursor.execute(upd_query, (new_done, task_id, session["user_id"]))
        conn.commit()
    conn.close()

    return get_tasks()


@app.route("/api/tasks/delete", methods=["POST"])
def delete_tasks():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    ids = data.get("ids", [])

    conn = get_db()
    cursor = conn.cursor()
    del_query = "DELETE FROM tasks WHERE id = %s AND user_id = %s" if DATABASE_URL else "DELETE FROM tasks WHERE id = ? AND user_id = ?"
    for task_id in ids:
        cursor.execute(del_query, (task_id, session["user_id"]))
    conn.commit()
    conn.close()

    return get_tasks()


# ---------- Note Routes ----------

@app.route("/api/notes")
def get_notes():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM notes WHERE user_id = %s" if DATABASE_URL else "SELECT * FROM notes WHERE user_id = ?"
    cursor.execute(query, (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    notes_data = [{"id": r["id"], "title": r["title"], "content": r["content"], "date": r["date"], "time": r["time"]} for r in rows]
    return jsonify(notes_data)


@app.route("/api/notes/add", methods=["POST"])
def add_note():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if title:
        now = datetime.datetime.now()
        conn = get_db()
        cursor = conn.cursor()
        query = "INSERT INTO notes (user_id, title, content, date, time) VALUES (%s, %s, %s, %s, %s)" if DATABASE_URL else "INSERT INTO notes (user_id, title, content, date, time) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, (session["user_id"], title, content, str(now.date()), str(now.time())))
        conn.commit()
        conn.close()

    return get_notes()


@app.route("/api/notes/delete", methods=["POST"])
def delete_notes():
    if login_required_json():
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    ids = data.get("ids", [])

    conn = get_db()
    cursor = conn.cursor()
    del_query = "DELETE FROM notes WHERE id = %s AND user_id = %s" if DATABASE_URL else "DELETE FROM notes WHERE id = ? AND user_id = ?"
    for note_id in ids:
        cursor.execute(del_query, (note_id, session["user_id"]))
    conn.commit()
    conn.close()

    return get_notes()


if __name__ == "__main__":
    app.run(debug=True)