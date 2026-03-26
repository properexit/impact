import geopandas as gpd
import requests
from io import BytesIO


WFS_URL = "https://geodienste-wasser.rlp-umwelt.de/geoserver/uesg/wfs"


def fetch_flood_gdf(bbox):
    """
    Fetch flood polygons from WFS (RLP)
    bbox: (minx, miny, maxx, maxy)
    """

    minx, miny, maxx, maxy = bbox

    # slight buffer to avoid edge miss
    buffer = 0.01
    minx -= buffer
    miny -= buffer
    maxx += buffer
    maxy += buffer

    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "uesg:ueberschwemmungsgebiete",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{minx},{miny},{maxx},{maxy},EPSG:4326"
    }

    try:
        res = requests.get(WFS_URL, params=params, timeout=20)

        if res.status_code != 200 or not res.content:
            print("⚠️ WFS request failed or empty")
            return None

        gdf = gpd.read_file(BytesIO(res.content))

        if gdf.empty:
            print("⚠️ WFS returned empty dataset")
            return None

        print(f"🌊 Flood polygons fetched: {len(gdf)}")

        return gdf

    except Exception as e:
        print("⚠️ Flood fetch error:", e)
        return None


def check_flood_risk(polygon, flood_gdf):
    """
    Check if polygon intersects flood zones
    """

    if flood_gdf is None or flood_gdf.empty:
        return None

    try:
        # ensure CRS match
        if flood_gdf.crs is None:
            flood_gdf.set_crs("EPSG:4326", inplace=True)

        if flood_gdf.crs.to_string() != "EPSG:4326":
            flood_gdf = flood_gdf.to_crs("EPSG:4326")

        intersects = flood_gdf.intersects(polygon)

        return bool(intersects.any())

    except Exception as e:
        print("⚠️ Flood check error:", e)
        return None