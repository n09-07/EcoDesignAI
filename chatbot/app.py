import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from user_history import init_db
from flask import Flask, request, jsonify, render_template, session
from chatbot.nlp_utils import extract_data
from sustainability_engine.decision_engine import generate_decision
from image.generator import generate_image

app = Flask(__name__)
# Required for session — set a real secret in production via env var
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ecodesignai-dev-secret")

init_db()
# ─────────────────────────────────────────────────────────────
# Material reference (for /api/material endpoint)
# ─────────────────────────────────────────────────────────────
MATERIAL_DATA = {
    "plastic": {
        "carbon": 8,
        "recyclable": "Partial",
        "cost": "Low",
        "durability": "High",
        "lifecycle": "High",
        "eco_score": 3
    },

    "bamboo": {
        "carbon": 2,
        "recyclable": "Yes",
        "cost": "Low",
        "durability": "Medium",
        "lifecycle": "Low",
        "eco_score": 9
    },

    "steel": {
        "carbon": 6,
        "recyclable": "Yes",
        "cost": "Medium",
        "durability": "High",
        "lifecycle": "Medium",
        "eco_score": 7
    },

    "aluminum": {
        "carbon": 3,
        "recyclable": "Yes",
        "cost": "Medium",
        "durability": "High",
        "lifecycle": "Medium",
        "eco_score": 8
    },

    "mycelium": {
        "carbon": 1,
        "recyclable": "Yes",
        "cost": "Medium",
        "durability": "Medium",
        "lifecycle": "Low",
        "eco_score": 10
    },

    "bioplastic": {
        "carbon": 4,
        "recyclable": "Yes",
        "cost": "Medium",
        "durability": "Medium",
        "lifecycle": "Low",
        "eco_score": 8
    }
}


# ─────────────────────────────────────────────────────────────
# Session state helpers
# Each browser tab gets its own session — no more shared global state
# ─────────────────────────────────────────────────────────────
BLANK = {
    "product":          None,
    "material":         None,
    "budget":           None,
    "eco_priority":     None,
    "durability":       None,
    "awaiting":         None,   # which slot we're currently asking for
    "material_options": None    # list of top-3 when in material_selection step
}

def get_state():
    if "conv" not in session:
        session["conv"] = dict(BLANK)
    return session["conv"]

def save_state(s):
    session["conv"] = s
    session.modified = True

def reset_state():
    session["conv"] = dict(BLANK)
    session.modified = True

def update_state(s, parsed):
    """Merge extracted slots — only overwrite if a real value was found."""
    for key in BLANK:
        val = parsed.get(key)
        if val is not None and val != "":
            s[key] = val

def missing_slots(s):
    gaps = []
    if not s["product"]:      gaps.append("product")
    if not s["budget"]:       gaps.append("budget")
    if not s["eco_priority"]: gaps.append("eco_priority")
    return gaps

def safe_dss(s, mat_row):
    """Build dss_output dict — never passes None to generate_image."""
    return {
        "product":       (s["product"]       or "product").lower(),
        "material":      (mat_row.get("material")      or "unknown"),
        "material_type": (mat_row.get("material_type") or "rigid"),
        "budget":        (s["budget"]        or "medium"),
        "eco_priority":  (s["eco_priority"]  or False),
        "durability":    (mat_row.get("durability")    or "medium")
    }


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.route("/debug/image")
def debug_image():
    """Visit /debug/image to see what images have been generated."""
    static_dir = os.path.join(os.path.dirname(__file__), "chatbot", "static", "generated_images")
    files = []
    if os.path.exists(static_dir):
        for root, dirs, filenames in os.walk(static_dir):
            for fn in filenames:
                rel = os.path.relpath(os.path.join(root, fn), 
                      os.path.join(os.path.dirname(__file__), "chatbot", "static"))
                files.append("/" + rel.replace("\\", "/"))
    return jsonify({"generated_images": files, "static_dir": static_dir})


@app.route("/")
def home():
    return jsonify({"message": "EcoDesignAI API is running!"})


@app.route("/design", methods=["POST"])
def design_product():
    try:
        body = request.get_json()
        if not body or "text" not in body:
            return jsonify({"error": "Please provide 'text' field"}), 400

        user_input = body["text"].strip()
        s          = get_state()
        user_lower = user_input.lower()

        print(f"\n[INPUT] {user_input!r}")
        print(f"[STATE] awaiting={s['awaiting']} product={s['product']} "
              f"budget={s['budget']} eco={s['eco_priority']} material={s['material']}")

        # ── STEP 1: Extract NLP data ─────────────────────────
        parsed = extract_data(user_input, expected_slot=s.get("awaiting"))
        print(f"[NLP]   {parsed}")

        # ── STEP 2: Handle 'skip' for eco_priority ───────────
        if s.get("awaiting") == "eco_priority" and \
                any(w in user_lower for w in ["skip", "any", "no preference"]):
            parsed["eco_priority"] = "recyclable"

        # ── STEP 3: Merge into state ──────────────────────────
        update_state(s, parsed)
        save_state(s)

        # ════════════════════════════════════════════════════
        # STATE MACHINE
        # ════════════════════════════════════════════════════

        # ── BRANCH A: User is picking a material ─────────────
        if s["awaiting"] == "material_selection":
            options  = s.get("material_options") or []
            selected = None

            # 1. Exact match against option names
            for opt in options:
                opt_name = opt["material"].lower().replace("_", " ")
                if opt_name in user_lower:
                    selected = opt["material"]
                    break

            # 2. First-word fuzzy match
            if not selected:
                for opt in options:
                    first = opt["material"].lower().replace("_", " ").split()[0]
                    if first in user_lower.split():
                        selected = opt["material"]
                        break

            # 3. "best / recommend / first" → pick top option
            if not selected and any(w in user_lower for w in
                    ["best", "recommend", "suggest", "you choose", "first", "top"]):
                selected = options[0]["material"]

            # 4. Couldn't understand — re-ask
            if not selected:
                return jsonify({
                    "clarification": "Please choose one of the materials below, or say 'recommend best'.",
                    "options": options
                })

            s["material"] = selected
            s["awaiting"] = None
            save_state(s)
            return _finalize(s)

        # ── BRANCH B: Collect missing slots one at a time ─────
        gaps = missing_slots(s)

        if "product" in gaps:
            s["awaiting"] = "product"
            save_state(s)
            return jsonify({
                "clarification": "What product would you like to design? (Bottle, Chair, Table, Shirt, etc.)"
            })

        if "budget" in gaps:
            s["awaiting"] = "budget"
            save_state(s)
            return jsonify({
                "clarification": "What is your budget? (Low / Medium / High)"
            })

        if "eco_priority" in gaps:
            s["awaiting"] = "eco_priority"
            save_state(s)
            return jsonify({
                "clarification": "What is your eco priority? (Low Carbon / Biodegradable / Recyclable) — or say 'skip'."
            })

        # ── BRANCH C: All slots filled — present material options
        hint = s.get("material")   # may be pre-set from studio button

        decision = generate_decision(
            product=s["product"],
            budget=s["budget"],
            eco_priority=s["eco_priority"],
            durability_req=s["durability"],
            preferred_material=hint
        )

        top_3 = decision.get("top_3_options", [])

        if not top_3:
            reset_state()
            return jsonify({
                "clarification": "No materials found matching those filters. Try a different budget or eco priority."
            })

        s["material"]         = None      # clear — user must confirm
        s["awaiting"]         = "material_selection"
        s["material_options"] = top_3
        save_state(s)

        hint_note = (f" <strong>{hint.replace('_',' ')}</strong> is highlighted based on your choice."
                     if hint else "")

        return jsonify({
            "clarification": (
                f"Here are the top materials for your <strong>{s['product']}</strong>."
                f"{hint_note} Choose one or say 'recommend best':"
            ),
            "options": top_3
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _finalize(s):
    """Generate final recommendation + image, then reset session."""

    decision = generate_decision(
        product=s["product"],
        budget=s["budget"],
        eco_priority=s["eco_priority"],
        durability_req=s["durability"],
        preferred_material=s["material"]
    )

    mat          = decision.get("recommended_material")
    product_name = s["product"] or "product"

    image_url = None
    if mat:
        try:
            image_url = generate_image(safe_dss(s, mat))
        except Exception as e:
            print(f"[IMAGE ERROR] {e}")

    reset_state()

    return jsonify({
        "final_recommendation": {
            "product":              product_name,
            "recommended_material": mat,
            "top_3_options":        decision.get("top_3_options"),
            "decision_explanation": decision.get("decision_explanation")
        },
        "eco_warning": decision.get("eco_warning"),
        "image_url":   image_url
    })


# ─────────────────────────────────────────────────────────────
# Other routes
# ─────────────────────────────────────────────────────────────

@app.route("/studio")
def studio():
    return render_template("studio.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/api/material/<name>")
def get_material(name):
    return jsonify(MATERIAL_DATA.get(name, {}))

if __name__ == "__main__":
    app.run(host="0.0.0.", port=5000)