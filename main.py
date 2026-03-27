import json
import os
from shapely.geometry import Polygon

from tools.osm_tool import fetch_osm_features
from tools.geo_utils import get_bbox, get_location_name, polygon_area_m2, validate_nrw_bounds
from tools.wfs_tool import fetch_flood_gdf, check_flood_risk, save_flood_overlay
from tools.wfs_nrw_tool import fetch_all_nrw_layers
from agents.browser_agent import run_browser_agent
from agents.report_agent import generate_report
import pandas as pd

from risk_engine import load_rules, evaluate_nrw

# ✅ NEW IMPORTS
from doc_ingestion import (
    extract_pdf_text,
    extract_csv,
    extract_image_text,
    build_doc_record
)


def load_polygon():
    path = "data/polygon.json"
    if not os.path.exists(path):
        raise FileNotFoundError("polygon.json not found. Please draw a polygon on the map first.")
    with open(path) as f:
        coords = json.load(f)
    return Polygon(coords)


def save_clean_jsonl(gdf, path="data/site_features.jsonl"):
    keys = ["natural", "waterway", "landuse", "amenity", "building", "leisure", "shop", "highway", "railway"]
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


def append_jsonl(record, path="data/site_features.jsonl"):
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


# ✅ UPDATED SIGNATURE (added uploaded_files)
def main(status_callback=print, uploaded_files=None):

    risk_score = 0  
    flags = []

    os.makedirs("data", exist_ok=True)

    status_callback("Loading polygon...")
    polygon = load_polygon()
    centroid = polygon.centroid
    lat, lon = centroid.y, centroid.x
    bbox = get_bbox(polygon)
    area = polygon_area_m2(polygon)
    status_callback(f"Centroid: {lat:.5f}°N, {lon:.5f}°E | Area: {area/10_000:.1f} ha")

    in_nrw = validate_nrw_bounds(lat, lon)
    if not in_nrw:
        status_callback("Location outside NRW — NRW WFS layers will be skipped.")

    status_callback("Reverse geocoding...")
    city, country, zip_code = get_location_name(lat, lon)
    location_info = {
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "city": city,
        "country": country,
        "zip_code": zip_code,
    }
    status_callback(f"   ✓ {city}, {country} ({zip_code})")

    jsonl_path = "data/site_features.jsonl"
    if os.path.exists(jsonl_path):
        os.remove(jsonl_path)

    status_callback("Fetching OpenStreetMap features...")
    try:
        gdf = fetch_osm_features(polygon)
        status_callback(f"OSM: {len(gdf)} features found")
        save_clean_jsonl(gdf, jsonl_path)
    except Exception as e:
        status_callback(f"OSM fetch failed: {e}")

    status_callback("Checking flood zones (RLP WFS)...")
    try:
        flood_gdf = fetch_flood_gdf(bbox)
        if flood_gdf is not None and not flood_gdf.empty:
            in_flood = check_flood_risk(polygon, flood_gdf)
            save_flood_overlay(flood_gdf, polygon)
            status_callback(f"   ✓ Flood risk: {'YES ⚠️' if in_flood else 'No'}")
        else:
            in_flood = None
            status_callback("No flood data returned")
    except Exception as e:
        in_flood = None
        status_callback(f"Flood WFS failed: {e}")

    append_jsonl({"type": "flood_signal", "flood_zone": in_flood}, jsonl_path)

    # ... everything unchanged above ...

    if in_nrw:
        status_callback("Fetching NRW WFS layers (ALKIS, geology, environment, topo)...")
        try:
            # ✅ FIX: use buffered polygon
            buffered_polygon = polygon.buffer(0.002)

            nrw_records = fetch_all_nrw_layers(
                buffered_polygon,   # ✅ changed
                bbox,
                status_callback=status_callback
            )

            for rec in nrw_records:
                if rec.get("status") == "found":
                    print(rec["label"])
                    print(rec["features"][:1])

            for record in nrw_records:
                append_jsonl(record, jsonl_path)

            found = sum(1 for r in nrw_records if r.get("status") == "found")
            status_callback(f"NRW layers: {found}/{len(nrw_records)} returned data")

            rules = load_rules()
            nrw_score, nrw_flags = evaluate_nrw(nrw_records, rules)

            risk_score += nrw_score
            flags.extend(nrw_flags)

            status_callback(f"NRW-derived risk: +{nrw_score}")

        except Exception as e:
            status_callback(f"NRW WFS failed: {e}")
    else:
        status_callback("Skipping NRW WFS (outside NRW bounds)")

    # ✅ NEW: USER DOCUMENT INGESTION
    if uploaded_files:
        status_callback("Processing uploaded documents...")
        for file in uploaded_files:
            try:
                if file.type == "application/pdf":
                    text = extract_pdf_text(file)
                    record = build_doc_record(text)

                elif file.type == "text/csv":
                    data = extract_csv(file)
                    record = {"type": "user_csv", "data": data}

                elif file.type.startswith("image"):
                    text = extract_image_text(file)
                    record = build_doc_record(text)

                else:
                    continue

                append_jsonl(record, jsonl_path)

            except Exception as e:
                status_callback(f"Failed to process {file.name}: {e}")

    status_callback("Running web research agent...")
    try:
        web_results = run_browser_agent(
            city=city,
            country=country,
            lat=lat,
            lon=lon,
            zip_code=zip_code,
            path=jsonl_path,
            status_callback=status_callback,
        )
    except Exception as e:
        status_callback(f"Browser agent failed: {e}")
        web_results = []

    web_flags = []
    web_risk = 0

    for r in web_results:
        text = (r.get("title", "") + " " + r.get("snippet", "")).lower()

        if "bebauungsplan" in text:
            web_flags.append("Zoning plan exists (check restrictions)")

        if "flächennutzungsplan" in text:
            web_flags.append("Land use plan applies")

        if "naturschutz" in text:
            web_flags.append("Protected area nearby")

        if "altlasten" in text:
            web_flags.append("Potential contaminated land")
            web_risk += 2

    flags.extend(web_flags)
    risk_score += web_risk

    status_callback(f"Web-derived risk: +{web_risk}")

    try:
        with open(jsonl_path) as f:
            for line in f:
                d = json.loads(line)

                if d.get("type") == "user_document":
                    text = d.get("text", "").lower()

                    if "naturschutz" in text:
                        flags.append("Protected area nearby (document)")
                        risk_score += 1

                    if "bebauungsplan" in text:
                        flags.append("Zoning plan exists (document)")

                    if "altlasten" in text:
                        flags.append("Potential contaminated land (document)")
                        risk_score += 2

                elif d.get("type") == "user_csv":
                    rows = d.get("data", {}).get("rows_sample", [])

                    for row in rows:
                        combined = str(row).lower()

                        if "altlasten" in combined:
                            flags.append("Potential contaminated land (CSV)")
                            risk_score += 2

                        if "bebauungsplan" in combined:
                            flags.append("Zoning plan exists (CSV)")

                        if "naturschutz" in combined:
                            flags.append("Protected area nearby (CSV)")
                            risk_score += 1

    except Exception as e:
        status_callback(f"Document parsing failed: {e}")

    status_callback("Generating due diligence report with Mistral...")
    report = generate_report(jsonl_path, location_info, risk_score, flags)
    report["risk_score"] = risk_score
    report["flags"] = list(set(flags))

    with open("data/last_report.json", "w") as f:
        json.dump(report, f, indent=2)

    status_callback("Report generated.")
    return report


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2) if isinstance(result, dict) else result)