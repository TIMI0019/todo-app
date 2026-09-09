from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import os
import re
import secrets
import resend  # Resend SDK for transactional emails

# --- App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-key")
app.permanent_session_lifetime = datetime.timedelta(days=30)

# Configure Resend API Key
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

DB_FILE = "todo.db"


# --- Helper Functions ---
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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Safely add optional/newer columns
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
            pass  # Column already exists

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
            cursor.execute(
                "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
                (username, hashed_password, email, phone)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("signup.html", error="That username is already taken.")

        new_user_id = cursor.lastrowid
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
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password"], password):
            return render_template("login.html", error="Incorrect username or password.")

        session.permanent = bool(remember_me)
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("home"))

    return render_template("login.html")


# Step 1: Render Request Page
@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    return render_template("forgot_password.html", step="request")


# Step 1 Handler: Generate & Send OTP Email
@app.route("/request-otp", methods=["POST"])
def request_otp():
    email = request.form.get("email", "").strip()
    print(f"\n--- [LOG] Reset request received for email: '{email}' ---", flush=True)

    if not email:
        print("--- [LOG] Error: Email parameter missing ---", flush=True)
        return render_template("forgot_password.html", step="request", error="Email is required.")

    # Verify if RESEND_API_KEY is configured
    if not RESEND_API_KEY:
        print("--- [LOG] WARNING: RESEND_API_KEY is not set in environment variables! ---", flush=True)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        print(f"--- [LOG] DB Check: No account found matching email '{email}' ---", flush=True)
    else:
        print(f"--- [LOG] DB Check: Found user '{user['username']}' (ID: {user['id']}) ---", flush=True)
        
        # Generate 6-digit numeric OTP and set 10-minute expiry
        otp = f"{secrets.randbelow(1000000):06d}"
        expiry = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()

        cursor.execute("UPDATE users SET otp = ?, otp_expiry = ? WHERE id = ?", (otp, expiry, user["id"]))
        conn.commit()
        print(f"--- [LOG] Generated OTP: {otp} | Expiry: {expiry} ---", flush=True)

        # Send Email via Resend
        print(f"--- [LOG] Sending email to '{email}' via Resend API... ---", flush=True)
        try:
            res = resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": [email],
                "subject": "Your Doneify Password Reset Code",
                "html": f"""
                    <h3>Password Reset Request</h3>
                    <p>Your 6-digit verification code is: <strong style="font-size: 20px;">{otp}</strong></p>
                    <p>This code will expire in 10 minutes.</p>
                """
            })
            print(f"--- [LOG] Resend Success! Response ID: {res} ---", flush=True)
        except Exception as e:
            print(f"--- [LOG] Resend API Error: {e} ---", flush=True)

    conn.close()

    # Always proceed to verify view to protect against user account enumeration
    return render_template("forgot_password.html", step="verify", email=email)


# Step 2 Handler: Verify OTP & Update Password
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
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        print("--- [LOG] Verification failed: User not found ---", flush=True)
        return render_template("forgot_password.html", step="verify", email=email, error="Invalid OTP code.")

    print(f"--- [LOG] DB OTP: '{user['otp']}' | DB Expiry: '{user['otp_expiry']}' ---", flush=True)

    if not user["otp"] or user["otp"] != otp or not user["otp_expiry"]:
        conn.close()
        print("--- [LOG] Verification failed: Invalid or mismatched OTP ---", flush=True)
        return render_template("forgot_password.html", step="verify", email=email, error="Invalid OTP code.")

    # Check OTP expiration
    expiry_time = datetime.datetime.fromisoformat(user["otp_expiry"])
    if datetime.datetime.now() > expiry_time:
        conn.close()
        print("--- [LOG] Verification failed: OTP expired ---", flush=True)
        return render_template("forgot_password.html", step="verify", email=email, error="OTP code has expired. Please request a new one.")

    # Update password and wipe used OTP
    hashed_password = generate_password_hash(new_password)
    cursor.execute(
        "UPDATE users SET password = ?, otp = NULL, otp_expiry = NULL WHERE id = ?",
        (hashed_password, user["id"])
    )
    conn.commit()
    conn.close()

    print("--- [LOG] Password updated successfully! ---", flush=True)
    return render_template("login.html", error="Password reset successfully. You can log in now.")


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
    cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    tasks_data = []
    for row in rows:
        tasks_data.append({
            "id": row["id"],
            "description": row["description"],
            "done": bool(row["done"])
        })
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
        cursor.execute(
            "INSERT INTO tasks (user_id, description, done) VALUES (?, ?, 0)",
            (session["user_id"], description)
        )
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
    cursor.execute(
        "SELECT done FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, session["user_id"])
    )
    row = cursor.fetchone()
    if row is not None:
        new_done = 0 if row["done"] else 1
        cursor.execute(
            "UPDATE tasks SET done = ? WHERE id = ? AND user_id = ?",
            (new_done, task_id, session["user_id"])
        )
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
    for task_id in ids:
        cursor.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        )
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
    cursor.execute("SELECT * FROM notes WHERE user_id = ?", (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    notes_data = []
    for row in rows:
        notes_data.append({
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "date": row["date"],
            "time": row["time"]
        })
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
        cursor.execute(
            "INSERT INTO notes (user_id, title, content, date, time) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], title, content, str(now.date()), str(now.time()))
        )
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
    for note_id in ids:
        cursor.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, session["user_id"])
        )
    conn.commit()
    conn.close()

    return get_notes()


if __name__ == "__main__":
    app.run(debug=True)