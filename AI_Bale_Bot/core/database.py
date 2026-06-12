import sqlite3
import time

conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role TEXT,
    content TEXT,
    ts INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    daily_count INTEGER DEFAULT 0,
    last_active INTEGER
)
""")

conn.commit()

def save_msg(uid, role, content):
    cur.execute(
        "INSERT INTO messages VALUES (NULL,?,?,?,?)",
        (uid, role, content, int(time.time()))
    )
    conn.commit()

def get_history(uid, limit):
    cur.execute(
        "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (uid, limit)
    )
    rows = cur.fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]

def get_users():
    cur.execute("SELECT * FROM users")
    return cur.fetchall()

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)",
                (uid, 0, int(time.time())))
    conn.commit()

def inc(uid):
    cur.execute("UPDATE users SET daily_count = daily_count + 1 WHERE user_id=?", (uid,))
    conn.commit()