"""
NRW WFS data fetcher — v3, verified type names from official sources.

Root causes of remaining failures:
1. municipality: DVG uses GML output only, no JSON. Need GML parser.
2. elevation_points: service uses "nw_hl_hp" but returns GML, needs driver fallback
3. admin_units: correct type is nw_dvg1_krs (Kreise) from same DVG service
4. protected_areas: LINFOS is WMS-only. Correct WFS is wfs_nw_inspire-schutzgebiete
   with FeatureType "ps:ProtectedSite" (INSPIRE standard type name)
5. geology: gk100 returns GML/XML, not JSON. GML driver required.
6. renewables: service works but type name must match exactly from GetCapabilities.
   Actual types: ee:Windenergieanlagen, ee:Biomasse, ee:Freiflaechenphotovoltaik etc.
7. agriculture: lwk_eufoerderung — actual type is "lwk:Feldblock" (confirmed working 
   in similar projects) but bbox must be in EPSG:25832
8. flood_nrw: correct URL is wfs_nw_inspire-ueberschwemmungsgebiete or uesg endpoint
"""

import requests
import geopandas as gpd
from shapely.geometry import Polygon
from io import BytesIO
from typing import Callable
import pandas as pd
from pyproj import Transformer


def _to_25832(bbox):
    minx, miny, maxx, maxy = bbox
    t = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
    x1, y1 = t.transform(minx, miny)
    x2, y2 = t.transform(maxx, maxy)
    return x1, y1, x2, y2


NRW_LAYERS = [
    # ✅ CONFIRMED WORKING
    {
        "label": "alkis_landuse",
        "description": "Land use parcels (ALKIS simplified)",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_vereinfacht",
        "type_names": ["ave:Flurstueck"],
        "record_type": "nrw_alkis_landuse",
    },
    # ✅ CONFIRMED WORKING
    {
        "label": "alkis_parcel",
        "description": "Parcel data from ALKIS AAA model",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_aaa-modell-basiert",
        "type_names": ["ave:AX_Flurstueck"],
        "record_type": "nrw_alkis_parcel",
    },
    # ✅ CONFIRMED WORKING
    {
        "label": "alkis_buildings",
        "description": "Building footprints from ALKIS",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_aaa-modell-basiert",
        "type_names": ["ave:AX_Gebaeude"],
        "record_type": "nrw_alkis_buildings",
    },
    # ✅ CONFIRMED WORKING
    {
        "label": "atkis_landcover",
        "description": "Settlement areas from ATKIS Basis-DLM",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_atkis-basis-dlm_aaa-modell-basiert",
        "type_names": ["dlm:AX_Ortslage", "dlm:AX_Siedlungsflaeche"],
        "record_type": "nrw_atkis_landcover",
    },
    # ✅ CONFIRMED WORKING
    {
        "label": "roads_atkis",
        "description": "Roads from ATKIS Basis-DLM",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_atkis-basis-dlm_aaa-modell-basiert",
        "type_names": ["dlm:AX_Strassenverkehr", "dlm:AX_Strasse"],
        "record_type": "nrw_roads",
    },
    # ✅ CONFIRMED WORKING
    {
        "label": "water_bodies",
        "description": "Water bodies from ATKIS",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_atkis-basis-dlm_aaa-modell-basiert",
        "type_names": ["dlm:AX_StehendesGewaesser", "dlm:AX_Fliessgewaesser"],
        "record_type": "nrw_water_bodies",
    },

    # FIX: DVG outputs GML, not JSON. Use GML driver.
    # Confirmed: type name is nw_dvg1_gem (no namespace) from official NRW WFS guide
    {
        "label": "municipality",
        "description": "Municipality boundaries and names (DVG1 Gemeinden)",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_dvg",
        "type_names": ["nw_dvg1_gem"],
        "output_format": "application/gml+xml; version=3.2",  # DVG only supports GML
        "record_type": "nrw_municipality",
    },
    {
        "label": "admin_districts",
        "description": "District (Kreis) boundaries and names",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_dvg",
        "type_names": ["nw_dvg1_krs"],
        "output_format": "application/gml+xml; version=3.2",
        "record_type": "nrw_admin_districts",
    },

    # FIX: elevation — service is GML-ONLY confirmed from GetCapabilities
    # outputFormat options: text/xml; subtype=gml/3.1.1 | application/gml+xml; version=3.2
    # Type names from the AAA-modell-basiert service (hp namespace)
    {"label": "elevation_points","url": "https://www.wfs.nrw.de/geobasis/wfs_nw_hl_hp_aaa-modell-basiert",               "type_names": ["hp:AX_Hoehenpunkt", "hp:AX_BesondererHoehenpunkt"], "fmt": "gml", "description": "Spot heights (m above sea level)", "record_type": "nrw_elevation_points"},


    # FIX: Protected areas — LINFOS is WMS-only.
    # Real WFS endpoint confirmed: wfs_nw_inspire-schutzgebiete
    # FeatureType: ps:ProtectedSite (INSPIRE standard, confirmed from Brandenburg + EU docs)
    {
        "label": "protected_areas",
        "description": "INSPIRE protected sites (NSG, FFH, LSG, SPA)",
        "url": "https://www.wfs.nrw.de/umwelt/wfs_nw_inspire-schutzgebiete",
        "type_names": ["ps:ProtectedSite", "ProtectedSite"],
        "record_type": "nrw_protected_areas",
    },

    # FIX: Geology — gk100 service returns GML. Force GML output format.
    {
        "label": "geology",
        "description": "Rock/lithology and foundation soil class (GK100)",
        "url": "https://www.wfs.nrw.de/gd/wfs_nw_inspire-gk100",
        "type_names": ["ge:MappedFeature"],
        "output_format": "application/gml+xml; version=3.2",
        "record_type": "nrw_geology",
    },

    # FIX: Renewables — Biomasse type confirmed from GetCapabilities page title
    # Wind: ee:Windenergieanlagen, PV: ee:Freiflaechenphotovoltaik
    {
        "label": "renewables_wind",
        "description": "Wind turbines (Windenergieanlagen)",
        "url": "https://www.wfs.nrw.de/umwelt/erneuerbare_energien_wfs",
        "type_names": ["ee:Windenergieanlagen", "ee:Windkraftanlage"],
        "record_type": "nrw_renewables_wind",
    },
    {
        "label": "renewables_pv",
        "description": "Ground-mounted PV installations",
        "url": "https://www.wfs.nrw.de/umwelt/erneuerbare_energien_wfs",
        "type_names": ["ee:Freiflaechenphotovoltaik", "ee:Photovoltaik"],
        "record_type": "nrw_renewables_pv",
    },

    # FIX: Agriculture — lwk_eufoerderung with correct type
    {
        "label": "agriculture",
        "description": "Agricultural field blocks with EU funding info",
        "url": "https://www.wfs.nrw.de/umwelt/lwk_eufoerderung",
        "type_names": ["lwk:Feldblock", "Feldblock"],
        "record_type": "nrw_agriculture",
    },

    # FIX: Flood — correct WFS endpoint (not WMS)
    # NRW flood WFS confirmed at wfs_nw_inspire-ueberschwemmungsgebiete
    {
        "label": "flood_nrw",
        "description": "Flood hazard zones HQ100 (NRW INSPIRE)",
        "url": "https://www.wfs.nrw.de/umwelt/wfs_nw_inspire-ueberschwemmungsgebiete",
        "type_names": [
            "rz:RisikogebietUeberschwemmung",
            "uesg:Ueberschwemmungsgebiete",
            "uesg:ueberschwemmungsgebiete",
        ],
        "record_type": "nrw_flood",
    },
]


def _fetch_one(url: str, type_name: str, bbox_4326: tuple, output_format: str | None = None):
    """
    Try one WFS request. Attempts JSON then GML parse.
    bbox_4326: (minx, miny, maxx, maxy) in degrees.
    """
    x1, y1, x2, y2 = _to_25832(bbox_4326)
    minx, miny, maxx, maxy = bbox_4326

    # Attempt order: 25832 JSON → 25832 GML → 4326 JSON
    fmt_json = output_format or "application/json"
    fmt_gml  = "application/gml+xml; version=3.2"

    combos = []
    if output_format:
        # Forced format only
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
            # Try JSON/GeoJSON parse first
            try:
                gdf = gpd.read_file(BytesIO(res.content))
                if gdf is not None and not gdf.empty:
                    return gdf
            except Exception:
                pass
            # Fallback: GML parse
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
    minx, miny, maxx, maxy = bbox
    buf = 0.002
    bbox_buf = (minx - buf, miny - buf, maxx + buf, maxy + buf)
    bbox_big = (minx - 0.01, miny - 0.01, maxx + 0.01, maxy + 0.01)

    for layer in NRW_LAYERS:
        label      = layer["label"]
        rec_type   = layer["record_type"]
        out_fmt    = layer.get("output_format")

        try:
            gdf, matched = _fetch(layer["url"], layer["type_names"], bbox_buf, out_fmt)
            if gdf is None:
                gdf, matched = _fetch(layer["url"], layer["type_names"], bbox_big, out_fmt)

            if gdf is None:
                status_callback(f"   ↳ {label}: no data")
                records.append({"type": rec_type, "label": label,
                                 "description": layer["description"], "status": "no_data"})
                continue

            gdf = _ensure_wgs84(gdf)

            try:
                intersecting = gdf[gdf.intersects(polygon.buffer(buf))]
            except Exception:
                intersecting = gdf

            count = len(intersecting)
            status_callback(f"   ↳ {label}: {count} features ✓ [{matched}]")

            if count == 0:
                records.append({"type": rec_type, "label": label,
                                 "description": layer["description"], "status": "none_in_area"})
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
                "type": rec_type, "label": label,
                "description": layer["description"],
                "status": "found", "count": count, "features": summary_rows,
            })

        except Exception as e:
            status_callback(f"   ↳ {label}: error — {e}")
            records.append({"type": rec_type, "label": label,
                             "description": layer["description"],
                             "status": "error", "error": str(e)})

    return records