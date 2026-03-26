import json
import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from tools.osm_tool import fetch_osm_features
from tools.geo_utils import get_bbox, get_location_name
from tools.wfs_tool import fetch_flood_gdf, check_flood_risk
from agents.browser_agent import run_browser_agent
from agents.report_agent import generate_report


def load_polygon():
    if not os.path.exists("data/polygon.json"):
        raise Exception("❌ polygon.json not found. Please draw polygon from UI.")

    with open("data/polygon.json") as f:
        coords = json.load(f)

    return Polygon(coords)


def save_clean_jsonl(gdf, path="data/site_features.jsonl"):
    keys = ["natural", "waterway", "landuse", "amenity", "building"]

    with open(path, "w") as f:
        for _, row in gdf.iterrows():
            record = {}

            for k in keys:
                val = row.get(k)
                if val is not None and pd.notna(val):
                    record[k] = str(val)

            if record:
                record["geometry"] = row.geometry.wkt
                f.write(json.dumps(record) + "\n")

    print("✅ Clean JSONL saved")


def save_flood_signal(in_flood, path="data/site_features.jsonl"):
    with open(path, "a") as f:
        record = {
            "type": "flood_signal",
            "flood_zone": in_flood
        }
        f.write(json.dumps(record) + "\n")


def main():
    print("🚀 Starting Site Analysis...")

    os.makedirs("data", exist_ok=True)

    if os.path.exists("data/site_features.jsonl"):
        os.remove("data/site_features.jsonl")

    polygon = load_polygon()
    print("📍 Polygon loaded")

    # 🔥 LOCATION INFO
    centroid = polygon.centroid
    lat, lon = centroid.y, centroid.x

    city, country = get_location_name(lat, lon)

    location_info = {
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "city": city,
        "country": country
    }

    # OSM
    gdf = fetch_osm_features(polygon)
    print(f"📊 Features found: {len(gdf)}")

    save_clean_jsonl(gdf)

    # FLOOD
    bbox = get_bbox(polygon)

    try:
        flood_gdf = fetch_flood_gdf(bbox)

        if flood_gdf is None:
            print("⚠️ No flood data available")
            in_flood = None
        else:
            print("📊 Flood GDF size:", len(flood_gdf))
            print("📐 Flood CRS:", flood_gdf.crs)

            in_flood = check_flood_risk(polygon, flood_gdf)

    except Exception as e:
        print("⚠️ Flood API failed:", e)
        in_flood = None

    print("🌊 Flood Risk:", in_flood)
    save_flood_signal(in_flood)

    # BROWSER
    print("🌐 Browser Agent running...")
    run_browser_agent(
    location_info["city"],
    location_info["country"],
    location_info["latitude"],
    location_info["longitude"]
)

    # REPORT
    print("\n📄 FINAL REPORT:\n")
    report = generate_report("data/site_features.jsonl", location_info)
    print(report)

    return report


if __name__ == "__main__":
    main()