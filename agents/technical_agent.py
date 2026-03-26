def technical_agent(geo_data):
    road = geo_data.get("distance_to_road")

    if road is None:
        access = "unknown"
    elif road < 200:
        access = "good"
    else:
        access = "poor"

    return {
        "accessibility": access,
        "road_distance_m": float(road) if road else None
    }