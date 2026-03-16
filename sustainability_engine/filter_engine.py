from .sustainability_db import load_materials
from .eco_score import calculate_eco_score


PRODUCT_MATERIAL_MAP = {
    "shirt": "textile", "tshirt": "textile", "t-shirt": "textile",
    "t shirt": "textile", "jacket": "textile", "pants": "textile",
    "clothes": "textile", "bag": "textile", "backpack": "textile", "shoe": "textile",
    "chair": "structural", "table": "structural", "sofa": "structural",
    "desk": "structural", "shelf": "structural", "bed": "structural",
    "cabinet": "structural", "stool": "structural", "stand": "structural", "rack": "structural",
    "bottle": "rigid", "cup": "rigid", "box": "rigid", "phone case": "rigid",
    "lamp": "rigid", "planter": "rigid", "notebook": "rigid", "helmet": "rigid",
    "bowl": "rigid", "plate": "rigid", "watch": "rigid"
}


def map_durability(value):
    return {"low": 1, "medium": 2, "high": 3}.get(str(value).lower(), 1)


def map_cost(value):
    return {"low": 3, "medium": 2, "high": 1}.get(str(value).lower(), 1)

def map_lifecycle_impact(value):
    return {"low": 3, "medium": 2, "high": 1}.get(str(value).lower(), 1)


def calculate_final_score(row, eco_priority=False):
    eco_w  = 0.4 if eco_priority else 0.25
    dur_w  = 0.25
    cost_w = 0.15
    life_w = 0.2

    return (
        row["eco_score"] * eco_w
        + map_durability(row.get("durability")) * 10 * dur_w
        + map_cost(row.get("cost_level")) * 10 * cost_w
        + map_lifecycle_impact(row.get("lifecycle_impact")) * 10 * life_w
    )


def filter_materials(product=None, budget=None, eco_priority=False,
                     min_durability=None, preferred_material=None):

    df = load_materials()
    if df is None or df.empty:
        return []

    df = df.copy()

    # Normalize preferred early
    preferred_norm = None
    if preferred_material:
        preferred_norm = preferred_material.lower().strip().replace("_", " ")

    # Keep a full snapshot before any filtering (for rescue later)
    full_df = df.copy()

    # ── Product type filter ──────────────────────────────────
    if product:
        product = product.strip().lower()
        if product in PRODUCT_MATERIAL_MAP:
            required_type = PRODUCT_MATERIAL_MAP[product]
            if "material_type" in df.columns:
                df = df[df["material_type"].str.lower() == required_type.lower()]

    # ── Budget filter ────────────────────────────────────────
    if budget and "cost_level" in df.columns:
        df = df[df["cost_level"].str.lower() == str(budget).lower()]

    # ── Durability filter ────────────────────────────────────
    if min_durability and "durability" in df.columns:
        df = df[df["durability"].str.lower() == min_durability.lower()]

    # ── Mark preferred in whatever survived filters ──────────
    if preferred_norm:
        df["preferred"] = df["material"].str.lower().str.replace("_", " ").str.contains(preferred_norm)
    else:
        df["preferred"] = False

    # ── Score & sort ─────────────────────────────────────────
    if not df.empty:
        df["eco_score"]   = df.apply(calculate_eco_score, axis=1)
        df["final_score"] = df.apply(lambda r: calculate_final_score(r, eco_priority), axis=1)
        df = df.sort_values(by=["preferred", "final_score"], ascending=[False, False])

    results = df.to_dict(orient="records") if not df.empty else []

    # ── Force-inject preferred if it was filtered out ────────
    if preferred_norm:
        already_present = any(
            preferred_norm in r.get("material", "").lower().replace("_", " ")
            for r in results
        )

        if not already_present:
            full_df["material_norm"] = full_df["material"].str.lower().str.replace("_", " ")
            matched = full_df[full_df["material_norm"].str.contains(preferred_norm, na=False)]

            if not matched.empty:
                row = matched.iloc[0].copy()
                row["eco_score"]   = calculate_eco_score(row)
                row["final_score"] = calculate_final_score(row, eco_priority)
                row["preferred"]   = True
                # Flag that this material was added despite not meeting filters
                row["user_forced"] = True
                results.insert(0, row.to_dict())

    return results

