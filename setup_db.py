import sqlite3

conn = sqlite3.connect("todo.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
""")
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
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
for column in columns:
    print(column)
    
print("\nUsers table created successfully.")

cursor.execute("PRAGMA table_info(tasks)")
columns = cursor.fetchall()
for column in columns:
    print(column)
    
print("\nTasks table created successfully.")

cursor.execute("PRAGMA table_info(notes)")
columns = cursor.fetchall()
for column in columns:
    print(column)    
conn.close()

print("Database and users table created.")

from werkzeug.security import generate_password_hash, check_password_hash

hashed = generate_password_hash("caleb123")
print(hashed)

is_correct = check_password_hash(hashed, "caleb123")
print(is_correct)

is_wrong = check_password_hash(hashed, "wrongpassword")
print(is_wrong)