import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify, render_template, session, redirect
from db_utils import init_db, save_history, get_db
from chatbot.nlp_utils import extract_data
from sustainability_engine.decision_engine import generate_decision
from werkzeug.security import generate_password_hash, check_password_hash
import traceback

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ecodesignai-dev-secret")

# Initialize DB
init_db()

# -------------------------
# BASIC ROUTES
# -------------------------

@app.route("/")
def home():
    if request.accept_mimetypes.accept_html:
        if 'user' in session:
            return redirect("/studio")
        return redirect("/login")
    
    return jsonify({"message": "EcoDesignAI API is running!"})

@app.route("/studio")
def studio():
    return render_template("studio.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

# -------------------------
# SIGNUP
# -------------------------

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
    else:
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

        if request.is_json:
            return jsonify({"redirect": "/login"})

        return redirect("/login")

    except Exception:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()

# -------------------------
# LOGIN
# -------------------------

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
    else:
        username = request.form.get('username')
        password = request.form.get('password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user'] = username

        if request.is_json:
            return jsonify({"redirect": "/studio"})

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
# DESIGN (optional route)
# -------------------------

@app.route("/design", methods=["POST"])
def design_product():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    try:
        body = request.get_json() or {}
        user_input = body.get("text", "")

        extracted = extract_data(user_input) or {}

        decision = generate_decision(
            product=extracted.get("product") or "chair",
            budget=extracted.get("budget") or "medium",
            eco_priority=extracted.get("eco") or extracted.get("eco_priority") or "recyclable",
            durability_req=extracted.get("durability") or "medium",
            user_name=session['user']
        )

        return jsonify(decision)

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Something went wrong",
            "details": str(e)
        }), 500

# -------------------------
# SAVE SELECTION
# -------------------------

@app.route("/select_material", methods=["POST"])
def select_material():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json() or {}
    product = data.get("product")
    material = data.get("material")

    save_history(session['user'], product, material)

    return jsonify({"message": "Saved successfully"})

# -------------------------
# CHAT (MAIN FIXED ROUTE)
# -------------------------

@app.route("/chat", methods=["POST"])
def chat():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    try:
        data = request.get_json() or {}

        # ✅ FIXED KEY
        user_input = data.get("text", "")

        if not user_input.strip():
            return jsonify({
                "error": "Empty input provided"
            }), 400

        # NLP
        extracted = extract_data(user_input) or {}

        print("\n--- DEBUG START ---")
        print("USER INPUT:", user_input)
        print("EXTRACTED:", extracted)

        # Safe values
        product = extracted.get("product") or "chair"
        budget = extracted.get("budget") or "medium"
        eco = extracted.get("eco") or extracted.get("eco_priority") or "recyclable"
        durability = extracted.get("durability") or "medium"

        preferred_material = extracted.get("material")

        print("FINAL INPUT TO DECISION:")
        print("Product:", product)
        print("Budget:", budget)
        print("Eco:", eco)
        print("Durability:", durability)
        print("--- DEBUG END ---\n")

        # Decision Engine
        decision = generate_decision(
            product=product,
            budget=budget,
            eco_priority=eco,
            durability_req=durability,
            preferred_material= preferred_material,
            user_name=session['user']
        )

        return jsonify(decision)

    except Exception as e:
        print("\n🔥 ERROR OCCURRED 🔥")
        traceback.print_exc()

        return jsonify({
            "error": "Something went wrong",
            "details": str(e)
        }), 500

# -------------------------

if __name__ == "__main__":
    app.run(debug=True)