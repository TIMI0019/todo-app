from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = "change-this-to-something-random-and-secret"

DB_FILE = "todo.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def login_required_json():
    """Returns True if the request should be blocked (no logged-in user)."""
    return "user_id" not in session


# ---------- Auth routes ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return render_template("signup.html", error="Username and password are required.")

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
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

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password"], password):
            return render_template("login.html", error="Incorrect username or password.")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session["username"])


# ---------- Task routes ----------

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


# ---------- Note routes ----------

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
