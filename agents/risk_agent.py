def risk_agent(geo_data):
    dist = geo_data.get("distance_to_water")

    if dist is None:
        return {"flood_risk": "unknown"}

    if dist < 100:
        risk = "high"
    elif dist < 500:
        risk = "medium"
    else:
        risk = "low"

    return {
        "flood_risk": risk,
        "distance_to_water_m": float(dist)
    }