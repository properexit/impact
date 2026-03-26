import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import requests

print("✅ Imports working")

# Geo test
point = Point(13.4050, 52.5200)
gdf = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326")
print("✅ GeoPandas OK")

# OSM test
features = ox.features_from_point((52.52, 13.4050), tags={"water": True}, dist=500)
print("✅ OSM OK:", len(features))

# API test
res = requests.get("https://httpbin.org/get")
print("✅ API OK:", res.status_code)