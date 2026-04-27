import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify, render_template, session, redirect
from db_utils import init_db, save_history, get_db
from chatbot.nlp_utils import extract_data
from sustainability_engine.decision_engine import generate_decision
from werkzeug.security import generate_password_hash, check_password_hash
import traceback
from image.generator import generate_image

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
def chatbot_page():
    return render_template("chatbot.html")

# -------------------------
# SIGNUP
# -------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    data = request.get_json() if request.is_json else request.form
    username = data.get('username')
    password = data.get('password')

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
    except Exception:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()

    return jsonify({"redirect": "/login"}) if request.is_json else redirect("/login")

# -------------------------
# LOGIN
# -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json() if request.is_json else request.form
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user'] = username
        return jsonify({"redirect": "/studio"}) if request.is_json else redirect("/studio")

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

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product, material, timestamp FROM history WHERE username=? ORDER BY timestamp DESC",
        (session['user'],)
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify({"history": [dict(row) for row in rows]})

# -------------------------
# DESIGN (Direct mode)
# -------------------------
@app.route("/design", methods=["POST"])
def design_product():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    try:
        body = request.get_json() or {}
        user_input = body.get("text", "")

        extracted = extract_data(user_input) or {}

        product = extracted.get("product")
        if not product:
            return jsonify({
                "error": "Could not understand product type. Please specify clearly."
            }), 400

        decision = generate_decision(
            product=product,
            budget=extracted.get("budget") or "medium",
            eco_priority=extracted.get("eco") or extracted.get("eco_priority") or "recyclable",
            durability_req=extracted.get("durability") or "medium",
            user_name=session['user']
        )

        return jsonify(decision)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Something went wrong", "details": str(e)}), 500

# -------------------------
# SAVE SELECTION
# -------------------------
@app.route("/select_material", methods=["POST"])
def select_material():
    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json() or {}
    save_history(session['user'], data.get("product"), data.get("material"))

    return jsonify({"message": "Saved successfully"})

# -------------------------
# CHAT (FINAL INTERACTIVE AI)
# -------------------------

VALID_LEVELS = {"low", "medium", "high"}

QUESTIONS = {
    "product":      "What product do you want to design?",
    "budget":       "What is your budget? (low / medium / high)",
    "eco_priority": "What is your eco priority? (low / medium / high)",
    "durability":   "How durable should it be? (low / medium / high)",
}

@app.route("/chat", methods=['GET', 'POST'])
def chat():
    if request.method == 'GET':
        return render_template("chat.html")

    if 'user' not in session:
        return jsonify({"error": "Login required"}), 401

    try:
        data = request.get_json() or {}
        user_input = data.get("text", "").strip()

        if not user_input:
            return jsonify({"error": "Empty input provided"}), 400

        # Initialize session conversation state
        if "conversation" not in session:
            session["conversation"] = {}

        conv = session["conversation"]

        # Run NLP extraction
        extracted = extract_data(user_input) or {}

        # ── ONE-FIELD-AT-A-TIME state machine ──────────────────────────
        # Find the first missing field and try to fill it from this message.
        # If the value is invalid, re-ask the same question.

        if not conv.get("product"):
            # Accept anything as product name
            product_val = extracted.get("product") or user_input
            conv["product"] = product_val
            session["conversation"] = conv
            session.modified = True
            return jsonify({"message": QUESTIONS["budget"]})

        elif not conv.get("budget"):
            val = (extracted.get("budget") or user_input).lower().strip()
            if val not in VALID_LEVELS:
                return jsonify({"message": "Please enter a valid budget: low, medium, or high."})
            conv["budget"] = val
            session["conversation"] = conv
            session.modified = True
            return jsonify({"message": QUESTIONS["eco_priority"]})

        elif not conv.get("eco_priority"):
            val = (extracted.get("eco_priority") or user_input).lower().strip()
            if val not in VALID_LEVELS:
                return jsonify({"message": "Please enter a valid eco priority: low, medium, or high."})
            conv["eco_priority"] = val
            session["conversation"] = conv
            session.modified = True
            return jsonify({"message": QUESTIONS["durability"]})

        elif not conv.get("durability"):
            val = (extracted.get("durability") or user_input).lower().strip()
            if val not in VALID_LEVELS:
                return jsonify({"message": "Please enter a valid durability level: low, medium, or high."})
            conv["durability"] = val
            session["conversation"] = conv
            session.modified = True
            # All fields collected — fall through to generate decision below

        # ── All fields collected → generate decision ───────────────────
        decision = generate_decision(
            product=conv["product"],
            budget=conv["budget"],
            eco_priority=conv["eco_priority"],
            durability_req=conv["durability"],
            user_name=session['user']
        )

        # Reset conversation after decision
        session["conversation"] = {}
        session.modified = True

        # Generate image
        recommended_material = decision.get("recommended_material", {}).get("material")
        image_url = None

        if recommended_material:
            dss_output = {
                "product": conv["product"],
                "material": recommended_material,
                "material_type": extracted.get("material_type", "generic"),
                "budget": conv["budget"],
                "eco_priority": conv["eco_priority"],
                "durability": conv["durability"]
            }
            image_url = generate_image(dss_output)

        return jsonify({**decision, "image_url": image_url})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Something went wrong", "details": str(e)}), 500

# -------------------------
if __name__ == "__main__":
    app.run(debug=True)