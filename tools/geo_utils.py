from shapely.geometry import Point

import geopandas as gpd
from shapely.geometry import Point

def compute_distance_to_features(point, gdf):
    if gdf is None or gdf.empty:
        return None

    # Convert to GeoDataFrame
    point_gdf = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326")

    # Project both to metric CRS (Germany → EPSG:3857 or 32632)
    gdf_proj = gdf.to_crs(epsg=3857)
    point_proj = point_gdf.to_crs(epsg=3857)

    distances = gdf_proj.geometry.distance(point_proj.geometry.iloc[0])

    return distances.min()