import geopandas as gpd
import requests
import json
import os
from io import BytesIO
from shapely.geometry import Polygon

WFS_URL = "https://geodienste-wasser.rlp-umwelt.de/geoserver/uesg/wfs"


def fetch_flood_gdf(bbox):
    """
    Fetch flood polygons from RLP WFS.
    bbox: (minx, miny, maxx, maxy)
    """
    minx, miny, maxx, maxy = bbox
    buf = 0.01
    minx -= buf; miny -= buf; maxx += buf; maxy += buf

    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "uesg:ueberschwemmungsgebiete",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{minx},{miny},{maxx},{maxy},EPSG:4326",
    }

    try:
        res = requests.get(WFS_URL, params=params, timeout=20)
        if res.status_code != 200 or not res.content:
            return None
        
        for fmt in ["application/json", "text/xml"]:
            params["outputFormat"] = fmt
            try:
                gdf = gpd.read_file(BytesIO(resp.content))
                if not gdf.empty:
                    return gdf
            except:
                continue
    except Exception as e:
        print(f"⚠️ Flood fetch error: {e}")
        return None


def check_flood_risk(polygon: Polygon, flood_gdf) -> bool | None:
    """Returns True if polygon intersects any flood zone."""
    if flood_gdf is None or flood_gdf.empty:
        return None
    try:
        if flood_gdf.crs is None:
            flood_gdf = flood_gdf.set_crs("EPSG:4326")
        elif flood_gdf.crs.to_epsg() != 4326:
            flood_gdf = flood_gdf.to_crs("EPSG:4326")
        return bool(flood_gdf.intersects(polygon).any())
    except Exception as e:
        print(f"⚠️ Flood check error: {e}")
        return None


def save_flood_overlay(flood_gdf, polygon: Polygon, path="data/flood_overlay.json"):
    """Save flood polygon coordinates for Folium map overlay."""
    if flood_gdf is None or flood_gdf.empty:
        return
    try:
        if flood_gdf.crs and flood_gdf.crs.to_epsg() != 4326:
            flood_gdf = flood_gdf.to_crs("EPSG:4326")
        overlapping = flood_gdf[flood_gdf.intersects(polygon)]
        polys = []
        for geom in overlapping.geometry:
            if geom.geom_type == "Polygon":
                polys.append(list(geom.exterior.coords))
            elif geom.geom_type == "MultiPolygon":
                for sub in geom.geoms:
                    polys.append(list(sub.exterior.coords))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(polys, f)
    except Exception as e:
        print(f"⚠️ Could not save flood overlay: {e}")