import osmnx as ox
from shapely.geometry import Polygon


OSM_TAGS = {
    "natural": True,
    "waterway": True,
    "landuse": True,
    "amenity": True,
    "building": True,
    "leisure": True,
    "shop": True,
    "highway": ["motorway", "trunk", "primary", "secondary"],
    "railway": True,
}


def fetch_osm_features(polygon: Polygon):
    """
    Fetch OSM features within the polygon.
    Returns a GeoDataFrame.
    """
    gdf = ox.features_from_polygon(polygon, tags=OSM_TAGS)
    return gdf