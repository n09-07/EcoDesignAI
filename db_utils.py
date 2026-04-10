import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "ecodesignai.db"

# DB file path (root folder)
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)


# -------------------------
# Get DB connection
# -------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


# -------------------------
# Initialize tables
# -------------------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # HISTORY TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            product TEXT,
            material TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # MATERIALS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            name TEXT PRIMARY KEY,
            sustainability_score INTEGER,
            cost TEXT,
            recyclability TEXT,
            usage TEXT
        )
    """)

    conn.commit()
    conn.close()


# -------------------------
# Add a new user
# -------------------------
def add_user(username, password):
    conn = get_db()
    cur = conn.cursor()
    hashed_pw = generate_password_hash(password)

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed_pw)
        )
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
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    return row and check_password_hash(row["password_hash"], password)


# -------------------------
# Save user history
# -------------------------
def save_history(username, product, material):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO history (username, product, material) VALUES (?, ?, ?)",
        (username, product, material)
    )

    conn.commit()
    conn.close()


# -------------------------
# Get user history
# -------------------------
def get_user_history(username):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT product, material, timestamp FROM history WHERE username=? ORDER BY timestamp DESC",
        (username,)
    )

    rows = cur.fetchall()
    conn.close()
    return rows


# -------------------------
# Get material data
# -------------------------
def get_material_data(material_name):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM materials WHERE LOWER(name)=LOWER(?)",
        (material_name,)
    )

    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "name": row["name"],
            "sustainability_score": row["sustainability_score"],
            "cost": row["cost"],
            "recyclability": row["recyclability"],
            "usage": row["usage"]
        }
    else:
        return None


# -------------------------
# Insert sample materials
# -------------------------
def insert_sample_materials():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO materials VALUES ('bioplastic', 4, 'medium', 'high', 'packaging')")
    cur.execute("INSERT OR IGNORE INTO materials VALUES ('glass', 5, 'high', 'very high', 'containers')")
    cur.execute("INSERT OR IGNORE INTO materials VALUES ('paper', 4, 'low', 'high', 'wrapping')")
    cur.execute("INSERT OR IGNORE INTO materials VALUES ('metal', 3, 'medium', 'recyclable', 'cans')")

    conn.commit()
    conn.close()


# -------------------------
# TEST BLOCK (run file directly)
# -------------------------
if __name__ == "__main__":
    print("Initializing database...")
    init_db()

    print("Inserting sample materials...")
    insert_sample_materials()

    material = input("\nEnter material name: ")
    data = get_material_data(material)

    if data:
        print("\nMaterial Found:")
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print("\nMaterial not found")