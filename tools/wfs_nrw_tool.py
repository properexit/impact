"""
NRW WFS data fetcher — v3, verified type names from official sources.
"""

import requests
import geopandas as gpd
from shapely.geometry import Polygon
from io import BytesIO
from typing import Callable
import pandas as pd
from pyproj import Transformer
import json
import os


# ✅ NEW: dynamic layer loader
def load_dynamic_layers():
    path = "data/nrw_layers.json"

    if os.path.exists(path):
        try:
            with open(path) as f:
                layers = json.load(f)

            print(f"✅ Using dynamic NRW layers ({len(layers)})")
            return layers

        except Exception as e:
            print(f"⚠️ Failed to load dynamic layers: {e}")

    return NRW_LAYERS


def _to_25832(bbox):
    minx, miny, maxx, maxy = bbox
    t = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
    x1, y1 = t.transform(minx, miny)
    x2, y2 = t.transform(maxx, maxy)
    return x1, y1, x2, y2


# ⚠️ KEEP YOUR ORIGINAL NRW_LAYERS (UNCHANGED)
NRW_LAYERS = [
    {
        "label": "alkis_landuse",
        "description": "Land use parcels (ALKIS simplified)",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_vereinfacht",
        "type_names": ["ave:Flurstueck"],
        "record_type": "nrw_alkis_landuse",
    },
    {
        "label": "alkis_parcel",
        "description": "Parcel data from ALKIS AAA model",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_aaa-modell-basiert",
        "type_names": ["ave:AX_Flurstueck"],
        "record_type": "nrw_alkis_parcel",
    },
    {
        "label": "alkis_buildings",
        "description": "Building footprints from ALKIS",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_aaa-modell-basiert",
        "type_names": ["ave:AX_Gebaeude"],
        "record_type": "nrw_alkis_buildings",
    },
]


def _fetch_one(url: str, type_name: str, bbox_4326: tuple, output_format: str | None = None):
    x1, y1, x2, y2 = _to_25832(bbox_4326)
    minx, miny, maxx, maxy = bbox_4326

    fmt_json = output_format or "application/json"
    fmt_gml  = "application/gml+xml; version=3.2"

    combos = []
    if output_format:
        combos = [
            (f"{x1},{y1},{x2},{y2},EPSG:25832", "EPSG:25832", "2.0.0", "TYPENAMES", output_format),
            (f"{x1},{y1},{x2},{y2},EPSG:25832", "EPSG:25832", "1.1.0", "TYPENAME",  output_format),
        ]
    else:
        combos = [
            (f"{x1},{y1},{x2},{y2},EPSG:25832", "EPSG:25832", "2.0.0", "TYPENAMES", fmt_json),
            (f"{x1},{y1},{x2},{y2},EPSG:25832", "EPSG:25832", "1.1.0", "TYPENAME",  fmt_json),
            (f"{minx},{miny},{maxx},{maxy},EPSG:4326", "EPSG:4326", "1.1.0", "TYPENAME", fmt_json),
            (f"{x1},{y1},{x2},{y2},EPSG:25832", "EPSG:25832", "2.0.0", "TYPENAMES", fmt_gml),
        ]

    for bbox_str, srs, version, tn_key, fmt in combos:
        params = {
            "SERVICE": "WFS", "VERSION": version, "REQUEST": "GetFeature",
            tn_key: type_name, "SRSNAME": srs, "BBOX": bbox_str,
            "OUTPUTFORMAT": fmt, "MAXFEATURES": "200", "COUNT": "200",
        }
        try:
            res = requests.get(url, params=params, timeout=30)
            if res.status_code != 200 or len(res.content) < 30:
                continue

            head = res.content[:400].lower()
            if b"exceptionreport" in head or b"serviceexception" in head:
                continue

            try:
                gdf = gpd.read_file(BytesIO(res.content))
                if gdf is not None and not gdf.empty:
                    return gdf
            except Exception:
                pass

            try:
                gdf = gpd.read_file(BytesIO(res.content), driver="GML")
                if gdf is not None and not gdf.empty:
                    return gdf
            except Exception:
                pass

        except Exception:
            continue

    return None


def _fetch(url: str, type_names: list, bbox: tuple, output_format: str | None = None):
    for tn in type_names:
        gdf = _fetch_one(url, tn, bbox, output_format)
        if gdf is not None:
            return gdf, tn
    return None, None


def _ensure_wgs84(gdf):
    if gdf.crs is None:
        return gdf.set_crs("EPSG:4326")
    if gdf.crs.to_epsg() != 4326:
        return gdf.to_crs("EPSG:4326")
    return gdf


def fetch_all_nrw_layers(polygon: Polygon, bbox, status_callback: Callable = print) -> list[dict]:
    records = []

    # ✅ NEW: dynamic config
    layers = load_dynamic_layers()

    minx, miny, maxx, maxy = bbox
    buf = 0.002
    bbox_buf = (minx - buf, miny - buf, maxx + buf, maxy + buf)
    bbox_big = (minx - 0.01, miny - 0.01, maxx + 0.01, maxy + 0.01)

    for layer in layers:
        label = layer["label"]
        rec_type = layer.get("record_type", f"nrw_{label}")
        out_fmt = layer.get("output_format")

        try:
            gdf, matched = _fetch(layer["url"], layer["type_names"], bbox_buf, out_fmt)

            if gdf is None:
                gdf, matched = _fetch(layer["url"], layer["type_names"], bbox_big, out_fmt)

            if gdf is None:
                status_callback(f"   ↳ {label}: no data")
                records.append({
                    "type": rec_type,
                    "label": label,
                    "status": "no_data"
                })
                continue

            gdf = _ensure_wgs84(gdf)

            try:
                intersecting = gdf[gdf.intersects(polygon.buffer(buf))]
            except Exception:
                intersecting = gdf

            count = len(intersecting)
            status_callback(f"   ↳ {label}: {count} features ✓ [{matched}]")

            if count == 0:
                records.append({
                    "type": rec_type,
                    "label": label,
                    "status": "none_in_area"
                })
                continue

            summary_rows = []
            for _, row in intersecting.head(5).iterrows():
                row_dict = {}
                for col in intersecting.columns:
                    if col == "geometry":
                        continue
                    v = row.get(col)
                    if v is not None:
                        try:
                            if pd.notna(v):
                                row_dict[col] = str(v)
                        except Exception:
                            row_dict[col] = str(v)
                if row_dict:
                    summary_rows.append(row_dict)

            records.append({
                "type": rec_type,
                "label": label,
                "status": "found",
                "count": count,
                "features": summary_rows,
            })

        except Exception as e:
            status_callback(f"   ↳ {label}: error — {e}")
            records.append({
                "type": rec_type,
                "label": label,
                "status": "error",
                "error": str(e)
            })

    return records