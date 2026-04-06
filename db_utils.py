import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "ecodesignai.db"

# DB file path (root folder)
DB_PATH = os.path.join(os.path.dirname(__file__), 'ecodesignai.db')


# -------------------------
# Get DB connection
# -------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows accessing columns by name
    return conn

# -------------------------
# Initialize tables
# -------------------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # USERS TABLE ✅
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # HISTORY TABLE (if already there, keep it)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            product TEXT,
            material TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

# -------------------------
# Add a new user
# -------------------------
def add_user(username, password, email=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    hashed_pw = generate_password_hash(password)
    try:
        cur.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?)",
                    (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# -------------------------
# Verify login credentials
# -------------------------
def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row and check_password_hash(row[0], password)

# Save user material history
def save_history(username, product, material):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO history (username, product, material) VALUES (?, ?, ?)",
                (username, product, material))
    conn.commit()
    conn.close()

# Get user history
def get_user_history(username):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT product, material, timestamp FROM history WHERE username=? ORDER BY timestamp DESC", (username,))
    rows = cur.fetchall()
    conn.close()
    return rows