import osmnx as ox

def get_nearby_water(lat, lon, radius=500):
    try:
        features = ox.features_from_point(
            (lat, lon),
            tags={"water": True},
            dist=radius
        )
        return features
    except Exception as e:
        print("OSM error:", e)
        return None