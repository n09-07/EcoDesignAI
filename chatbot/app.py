import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify, render_template, session, redirect
from db_utils import init_db, save_history, get_db
from chatbot.nlp_utils import extract_data
from sustainability_engine.decision_engine import generate_decision
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ecodesignai-dev-secret")

# Initialize DB
init_db()

# -------------------------
# BASIC ROUTES
# -------------------------

@app.route("/")
def home():
    # If request is from browser → redirect
    if request.accept_mimetypes.accept_html:
        if 'user' in session:
            return redirect("/studio")
        return redirect("/login")
    
    # Otherwise (API/testing) → return JSON
    return jsonify({"message": "EcoDesignAI API is running!"})

@app.route("/studio")
def studio():
    return render_template("studio.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

# -------------------------
# SIGNUP (GET + POST)
# -------------------------

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    hashed_password = generate_password_hash(password)

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        return redirect("/login")
    except Exception:
        return "Username already exists", 400
    finally:
        conn.close()

# -------------------------
# LOGIN (GET + POST)
# -------------------------

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user'] = username   # ✅ store username
        return redirect("/studio")
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# -------------------------
# LOGOUT
# -------------------------

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect("/login")

# -------------------------
# HISTORY
# -------------------------

@app.route('/history')
def history():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    username = session['user']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product, material, timestamp FROM history WHERE username=? ORDER BY timestamp DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify({"history": [dict(row) for row in rows]})

# -------------------------
# DESIGN (PROTECTED)
# -------------------------

@app.route("/design", methods=["POST"])
def design_product():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    body = request.get_json()
    user_input = body.get("text", "")

    decision = generate_decision(
        product="chair",
        budget="medium",
        eco_priority="recyclable",
        durability_req="medium",
        user_name=session['user']
    )

    return jsonify(decision)

# -------------------------
# SAVE SELECTION
# -------------------------

@app.route("/select_material", methods=["POST"])
def select_material():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json()
    product = data.get("product")
    material = data.get("material")

    save_history(session['user'], product, material)

    return jsonify({"message": "Saved successfully"})

# -------------------------

if __name__ == "__main__":
    app.run(debug=True)