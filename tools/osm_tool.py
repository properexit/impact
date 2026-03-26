import osmnx as ox


def fetch_osm_features(polygon):
    tags = {
        "natural": True,
        "waterway": True,
        "landuse": True,
        "amenity": True,
        "building": True
    }

    return ox.features_from_polygon(polygon, tags)