from .filter_engine import filter_materials
from chatbot.user_history import save_history

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
        if value == "high":   return "Highly durable"
        elif value == "medium": return "Moderately durable"
        else:                   return "Low durability"
    return "Unknown durability"


def generate_decision(product=None, budget=None, eco_priority=False,
                      durability_req=None, preferred_material=None):

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
    top_3        = materials[:3]
    # save recommendation to database
    save_history(product, top_material.get("material"))

    carbon_meaning    = interpret_carbon(top_material.get("carbon_score", 0))
    durability_meaning = interpret_durability(top_material.get("durability", ""))

    # ── Build explanation ────────────────────────────────────
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
        f"This material provides the best overall balance between "
        f"environmental impact, durability, and cost efficiency "
        f"based on your selected preferences."
    )

    # ── Add eco warning if user forced a non-eco material ────
    eco_warning = None
    if top_material.get("user_forced"):
        mat_name    = top_material.get("material", "").replace("_", " ")
        carbon      = top_material.get("carbon_score", "?")
        eco_score   = top_material.get("eco_score", "?")
        recyclable  = top_material.get("recyclable", "?")
        eco_warning = (
            f"⚠️ Heads up: {mat_name} doesn't match your eco/budget filters, "
            f"but we've included it since you specifically requested it.\n\n"
            f"Eco profile for {mat_name}: Carbon Score {carbon} ({interpret_carbon(carbon if isinstance(carbon, (int,float)) else 0)}), "
            f"Eco Score {eco_score}, Recyclable: {recyclable}.\n\n"
            f"Consider one of the greener alternatives below if sustainability is a priority."
        )

    return {
        "product":              product,
        "recommended_material": top_material,
        "top_3_options":        top_3,
        "decision_explanation": explanation.strip(),
        "eco_warning":          eco_warning   # None if no issue, string if forced
    }

def sustainability_score(material):

    score = 0

    # lower carbon is better
    score += max(0, 100 - material["carbon_score"]) * 0.3

    # recyclability
    if material["recyclable"] == "yes":
        score += 20

    # biodegradability
    if material["biodegradable"] == "yes":
        score += 20

    # durability
    durability_scores = {
        "low": 5,
        "medium": 10,
        "high": 15
    }

    score += durability_scores.get(material["durability"], 0)

    # lifecycle
    lifecycle_scores = {
        "low": 15,
        "medium": 10,
        "high": 5
    }

    score += lifecycle_scores.get(material["lifecycle_impact"], 0)

    return score