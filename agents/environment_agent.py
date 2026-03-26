def environment_agent(geo_data):
    dist = geo_data.get("distance_to_water")

    if dist is None:
        return {"env_risk": "unknown"}

    if dist < 100:
        risk = "high"
    elif dist < 500:
        risk = "medium"
    else:
        risk = "low"

    return {
        "env_risk": risk,
        "water_distance_m": float(dist)
    }