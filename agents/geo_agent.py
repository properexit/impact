from shapely.geometry import Point
from tools.geo_utils import compute_distance_to_features

def geo_agent(lat, lon, data):
    point = Point(lon, lat)

    water_gdf = data.get("water")

    distance = compute_distance_to_features(point, water_gdf)

    return {
        "distance_to_water": distance
    }