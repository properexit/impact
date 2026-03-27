"""
NRW WFS data fetcher.
Fixes: WFS 1.1.0 + correct TYPENAME param + proper bbox lon/lat order + multiple type name candidates.
"""

import requests
import geopandas as gpd
from shapely.geometry import Polygon
from io import BytesIO
from typing import Callable
import pandas as pd

from pyproj import Transformer

def _bbox_to_25832(bbox):
    minx, miny, maxx, maxy = bbox
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)

    minx2, miny2 = transformer.transform(minx, miny)
    maxx2, maxy2 = transformer.transform(maxx, maxy)

    return minx2, miny2, maxx2, maxy2
    
NRW_LAYERS = [
    {
        "label": "alkis_landuse",
        "description": "Land use and building presence (ALKIS simplified)",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_vereinfacht",
        "type_names": ["ave:Flurstueck", "nw_ave:Flurstueck"],
        "record_type": "nrw_alkis_landuse",
    },
    {
        "label": "alkis_parcel",
        "description": "Parcel area, ownership type, protection status",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_aaa-modell-basiert",
        "type_names": ["ave:AX_Flurstueck", "AX_Flurstueck"],
        "record_type": "nrw_alkis_parcel",
    },
    {
        "label": "alkis_address",
        "description": "Official address, land use code, actual use",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_nas-konform",
        "type_names": ["ax:Flurstueck", "nw_nas:Flurstueck"],
        "record_type": "nrw_alkis_address",
    },
    {
        "label": "atkis_landcover",
        "description": "Land cover class, imperviousness, surface sealing",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_atkis-basis-dlm_aaa-modell-basiert",
        "type_names": ["dlm:AX_Ortslage", "dlm:AX_SiedlungsFlaeche"],
        "record_type": "nrw_atkis_landcover",
    },
    {
        "label": "municipality",
        "description": "Municipality name, AGS key, district",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_dvg",
        "type_names": ["nw_dvg:nw_dvg_gem", "dvg:dvg_gem"],
        "record_type": "nrw_municipality",
    },
    {
        "label": "elevation_model",
        "description": "Elevation and slope class",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_hl_hp_aaa-modell-basiert",
        "type_names": ["hp:AX_Hoehenpunkt", "AX_Hoehenpunkt"],
        "record_type": "nrw_elevation",
    },
    {
        "label": "elevation_points",
        "description": "Spot elevation values",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_hl_hp",
        "type_names": ["hp:Hoehenpunkt", "nw_hp:Hoehenpunkt"],
        "record_type": "nrw_elevation_points",
    },
    {
        "label": "admin_units",
        "description": "Administrative level, NUTS code",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_inspire-verwaltungseinheiten_atkis-basis-dlm",
        "type_names": ["au:AdministrativeUnit", "au:AdministrativeBoundary"],
        "record_type": "nrw_admin",
    },
    {
        "label": "transport_network",
        "description": "Road category, public transport access",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_inspire-verkehrsnetze_atkis-basis-dlm",
        "type_names": ["tn-ro:RoadLink", "tn-ro:Road"],
        "record_type": "nrw_transport",
    },
    {
        "label": "water_bodies",
        "description": "Water body type within buffer",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_inspire-gewaesser-physisch_atkis-basis-dlm",
        "type_names": ["hy-p:StandingWater", "hy-p:Waterbody"],
        "record_type": "nrw_water_bodies",
    },
    {
        "label": "water_network",
        "description": "Stream order, distance to watercourse",
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_inspire-gewaesser-netzwerk_atkis-basis-dlm",
        "type_names": ["hy-n:WatercourseLink", "hy-n:HydroNode"],
        "record_type": "nrw_water_network",
    },
    {
        "label": "geology",
        "description": "Rock/lithology type, foundation soil class",
        "url": "https://www.wfs.nrw.de/gd/wfs_nw_inspire-gk100",
        "type_names": ["ge:MappedFeature", "ge:GeologicUnit"],
        "record_type": "nrw_geology",
    },
    {
        "label": "protected_areas",
        "description": "NSG/FFH/LSG/SPA protected area status",
        "url": "https://www.wfs.nrw.de/umwelt/linfos",
        "type_names": [
            "linfos:Naturschutzgebiete",
            "linfos:FFH_Gebiete",
            "linfos:Landschaftsschutzgebiete",
        ],
        "record_type": "nrw_protected_areas",
    },
    {
        "label": "renewables",
        "description": "Renewable energy plants within 1km",
        "url": "https://www.wfs.nrw.de/umwelt/erneuerbare_energien_wfs",
        "type_names": ["ee:Windkraftanlage", "ee:Photovoltaik"],
        "record_type": "nrw_renewables",
    },
    {
        "label": "agriculture",
        "description": "Agricultural parcels, land use type",
        "url": "https://www.wfs.nrw.de/umwelt/lwk_eufoerderung",
        "type_names": ["lwk:Feldblock", "lwk:LandwirtschaftlicheFlaeche"],
        "record_type": "nrw_agriculture",
    },
    {
        "label": "flood_nrw",
        "description": "NRW flood hazard HQ100",
        "url": "https://www.wfs.nrw.de/umwelt/uesg",
        "type_names": ["uesg:Ueberschwemmungsgebiete", "uesg:ueberschwemmungsgebiete"],
        "record_type": "nrw_flood",
    },
]


def _wfs_fetch_one(url, type_name, bbox):
    """Single WFS attempt with fallback formats."""
    # convert bbox
    bbox_25832 = _bbox_to_25832(bbox)
    minx, miny, maxx, maxy = bbox_25832

    base_params = {
    "SERVICE": "WFS",
    "REQUEST": "GetFeature",
    "TYPENAME": type_name,
    "SRSNAME": "EPSG:25832",   # ✅ changed
    "BBOX": f"{minx},{miny},{maxx},{maxy},EPSG:25832",  # ✅ changed
    "MAXFEATURES": "200",
}

    # Try formats in order: GeoJSON → GML
    for version, output_format in [
        ("2.0.0", "application/json"),   # best case
        ("1.1.0", "application/json"),   # sometimes works
        ("1.1.0", "text/xml"),           # fallback (GML)
    ]:
        params = base_params.copy()
        params["VERSION"] = version
        params["OUTPUTFORMAT"] = output_format

        try:
            res = requests.get(url, params=params, timeout=30)

            if res.status_code != 200 or len(res.content) < 50:
                continue

            # Detect server-side error response
            head = res.content[:500].lower()
            if b"exception" in head or b"serviceexception" in head:
                continue

            gdf = gpd.read_file(BytesIO(res.content))

            if gdf is not None and not gdf.empty:
                return gdf

        except Exception:
            continue

    return None

def _wfs_fetch(url, type_names, bbox):
    for tn in type_names:
        gdf = _wfs_fetch_one(url, tn, bbox)
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
    buf = 0.002  # ~200m
    bbox_buf = (minx - buf, miny - buf, maxx + buf, maxy + buf)

    for layer in NRW_LAYERS:
        label = layer["label"]
        rec_type = layer["record_type"]
        try:
            gdf, matched = _wfs_fetch(layer["url"], layer["type_names"], bbox_buf)

            if gdf is None:
                status_callback(f"   ↳ {label}: no data")
                records.append({"type": rec_type, "label": label, "description": layer["description"], "status": "no_data"})
                continue

            gdf = _ensure_wgs84(gdf)
            intersecting = gdf[gdf.intersects(polygon.buffer(buf))]
            count = len(intersecting)
            status_callback(f"   ↳ {label}: {count} features ✓")

            if intersecting.empty:
                records.append({"type": rec_type, "label": label, "description": layer["description"], "status": "none_in_area"})
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
                "type": rec_type, "label": label, "description": layer["description"],
                "status": "found", "count": count, "features": summary_rows,
            })

        except Exception as e:
            status_callback(f"   ↳ {label}: error — {e}")
            records.append({"type": rec_type, "label": label, "description": layer["description"], "status": "error", "error": str(e)})

    return records