from .filter_engine import filter_materials
from db_utils import save_history


def interpret_carbon(score):
    if score <= 30:
        return "Low carbon impact"
    elif score <= 60:
        return "Moderate carbon impact"
    else:
        return "High carbon impact"


def interpret_durability(value):
    if isinstance(value, str):
        value = value.lower()
        if value == "high": return "Highly durable"
        elif value == "medium": return "Moderately durable"
        else: return "Low durability"
    return "Unknown durability"


# ✅ FIXED FUNCTION
def generate_decision(product=None, budget=None, eco_priority=False,
                      durability_req=None, preferred_material=None,
                      user_name=None):   # ✅ ADDED

    materials = filter_materials(
        product=product,
        budget=budget,
        eco_priority=eco_priority,
        min_durability=durability_req,
        preferred_material=preferred_material
    )

    if not materials:
        return {
            "product": product,
            "recommended_material": None,
            "top_3_options": [],
            "decision_explanation": "No suitable materials found based on selected constraints."
        }

    top_material = materials[0]
    top_3 = materials[:3]

    # ✅ FIX: correct DB save
    if user_name:
        save_history(user_name, product, top_material.get("material"))

    carbon_meaning = interpret_carbon(top_material.get("carbon_score", 0))
    durability_meaning = interpret_durability(top_material.get("durability", ""))

    explanation = (
        f"For designing a {product}, the most suitable material is "
        f"{top_material.get('material')}.\n\n"
        f"Sustainability Profile:\n"
        f"• Carbon Score: {top_material.get('carbon_score')} ({carbon_meaning})\n"
        f"• Eco Score: {top_material.get('eco_score')}\n"
        f"• Final Sustainability Score: {round(top_material.get('final_score', 0), 2)}\n"
        f"• Recyclable: {top_material.get('recyclable')}\n"
        f"• Biodegradable: {top_material.get('biodegradable')}\n"
        f"• Durability: {top_material.get('durability')} ({durability_meaning})\n\n"
        f"This material provides the best balance between "
        f"environmental impact, durability, and cost efficiency."
    )

    eco_warning = None
    if top_material.get("user_forced"):
        mat_name = top_material.get("material", "").replace("_", " ")
        carbon = top_material.get("carbon_score", "?")
        eco_score = top_material.get("eco_score", "?")
        recyclable = top_material.get("recyclable", "?")

        eco_warning = (
            f"⚠️ Heads up: {mat_name} doesn't match your filters, "
            f"but we included it since you requested it.\n\n"
            f"Carbon Score: {carbon} ({interpret_carbon(carbon if isinstance(carbon,(int,float)) else 0)})\n"
            f"Eco Score: {eco_score}\n"
            f"Recyclable: {recyclable}\n\n"
            f"Consider greener alternatives below."
        )

    return {
        "product": product,
        "recommended_material": top_material,
        "top_3_options": top_3,
        "decision_explanation": explanation.strip(),
        "eco_warning": eco_warning
    }


# (no change needed here)
def sustainability_score(material):

    score = 0

    score += max(0, 100 - material["carbon_score"]) * 0.3

    if material["recyclable"] == "yes":
        score += 20

    if material["biodegradable"] == "yes":
        score += 20

    durability_scores = {
        "low": 5,
        "medium": 10,
        "high": 15
    }
    score += durability_scores.get(material["durability"], 0)

    lifecycle_scores = {
        "low": 15,
        "medium": 10,
        "high": 5
    }
    score += lifecycle_scores.get(material["lifecycle_impact"], 0)

    return score