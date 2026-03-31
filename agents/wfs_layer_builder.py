import requests
import xml.etree.ElementTree as ET
from io import BytesIO
import geopandas as gpd
import json
import subprocess
from pathlib import Path
import re


# -------------------------------
# STEP 0: CLEAN SAMPLE
# -------------------------------
def clean_sample(row_dict):
    clean = {}

    for k, v in row_dict.items():
        try:
            if k == "geometry":
                continue

            if hasattr(v, "item"):
                v = v.item()

            if isinstance(v, (list, tuple)):
                v = str(v)

            clean[k] = str(v)

        except Exception:
            clean[k] = str(v)

    return dict(list(clean.items())[:10])


# -------------------------------
# STEP 1: Get feature types
# -------------------------------
def get_feature_types(wfs_url):
    url = f"{wfs_url}?service=WFS&request=GetCapabilities"

    try:
        res = requests.get(url, timeout=20)
        root = ET.fromstring(res.content)

        feature_types = []

        for elem in root.iter():
            if elem.tag.endswith("FeatureType"):
                for child in elem:
                    if child.tag.endswith("Name"):
                        feature_types.append(child.text)

        return feature_types

    except Exception:
        return []


# -------------------------------
# STEP 2: Validate typename
# -------------------------------
def test_typename(wfs_url, typename):
    params = {
        "SERVICE": "WFS",
        "REQUEST": "GetFeature",
        "VERSION": "1.1.0",
        "TYPENAME": typename,
        "MAXFEATURES": "5",
    }

    try:
        res = requests.get(wfs_url, params=params, timeout=20)

        if res.status_code != 200 or len(res.content) < 200:
            return False, None

        gdf = gpd.read_file(BytesIO(res.content))

        if gdf is None or gdf.empty:
            return False, None

        sample = clean_sample(gdf.iloc[0].to_dict())
        return True, sample

    except Exception:
        return False, None


# -------------------------------
# STEP 3: LOCAL LLM CALL
# -------------------------------
def call_local_llm(prompt):
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral"],
            input=prompt.encode(),
            stdout=subprocess.PIPE,
        )
        return result.stdout.decode()

    except Exception as e:
        print(f"LLM failed: {e}")
        return "[]"


# -------------------------------
# STEP 3.5: SAFE JSON EXTRACTION
# -------------------------------
def extract_json(text):
    try:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


# -------------------------------
# STEP 4: NORMALIZE LABEL
# -------------------------------
def normalize_label(typename):
    name = typename.split(":")[-1]
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return name.lower()


# -------------------------------
# STEP 5: LLM FILTER
# -------------------------------
def llm_filter(valid_layers):
    prompt = f"""
You are a geospatial data engineer.

Select ONLY useful layers.

STRICT:
- One typename per item
- No grouping
- Use only given typenames
- Return JSON only

FORMAT:
[
  {{
    "label": "snake_case",
    "type_names": ["typename"]
  }}
]

INPUT:
{json.dumps(valid_layers, indent=2)}
"""

    response = call_local_llm(prompt)
    parsed = extract_json(response)

    if not parsed:
        print("⚠️ LLM parsing failed")
        return []

    clean = []
    for item in parsed:
        if "type_names" not in item:
            continue

        if len(item["type_names"]) != 1:
            continue

        typename = item["type_names"][0]

        clean.append({
            "label": normalize_label(typename),
            "type_names": [typename]
        })

    return clean


# -------------------------------
# STEP 6: SEMANTIC FALLBACK
# -------------------------------
def fallback_filter(valid_layers):
    print("⚠️ Using refined semantic fallback")

    INCLUDE = [
        # core cadastre / land
        "flurstueck",
        "nutzung",
        "landwirtschaft",
        "gewerbe",
        "industrie",

        # buildings
        "gebaeude",
        "bauwerk",

        # transport
        "strassenverkehr",
        "strasse",
        "bahn",

        # water
        "gewaesser",
        "fluss",
        "kanal",

        # environment
        "schutz",
        "protectedsite",
        "natur",
        "ffh",
        "nsg",
        "lsg",

        # energy
        "windenergie",
        "photovoltaik",
        "pv",
        "biomasse",
        "wasserkraft",

        # terrain / elevation
        "hoehenpunkt",

        # admin (keep only important ones)
        "gemeinde",
        "kreis"
    ]

    EXCLUDE = [
        # geometry / rendering junk
        "darstellung",
        "linie",
        "punkt",
        "achse",
        "prozess",
        "po",
        "pto",
        "lpo",

        # internal / metadata
        "beschreibung",
        "presentation",
        "label",
        "annotation",

        # too granular / useless
        "besonder",
        "grenze",
        "gemarkung",
        "flur",
        "dienststelle",
        "buchungsblatt",
        "historisch",

        # noise from agri datasets
        "historische",
        "beantragte",
        "topup",
        "suchkulisse",
    ]

    selected = []

    for v in valid_layers:
        t = v["typename"].lower()

        # ❌ remove noise first
        if any(k in t for k in EXCLUDE):
            continue

        # ✅ include only strong signals
        if any(k in t for k in INCLUDE):
            selected.append({
                "label": normalize_label(v["typename"]),
                "type_names": [v["typename"]]
            })

    return selected

# -------------------------------
# STEP 7: BUILD CONFIG
# -------------------------------
def build_config(wfs_url, selected):
    config = []

    for item in selected:
        config.append({
            "label": item["label"],
            "url": wfs_url,
            "type_names": item["type_names"],
            "record_type": f"nrw_{item['label']}",
        })

    return config


# -------------------------------
# MAIN PIPELINE
# -------------------------------
def generate_nrw_layers(input_file="links.txt", output_file="data/nrw_layers.json"):
    Path("data").mkdir(exist_ok=True)

    with open(input_file) as f:
        urls = [l.strip() for l in f if l.strip()]

    final_config = []

    for url in urls:
        print(f"\n🔍 Processing {url}")

        types = get_feature_types(url)
        print(f"→ {len(types)} feature types")

        valid_layers = []

        for t in types[:80]:  # ✅ deeper exploration
            ok, sample = test_typename(url, t)

            if ok:
                print(f"   ✅ {t}")
                valid_layers.append({
                    "typename": t,
                    "sample": sample
                })

        if not valid_layers:
            continue

        selected = llm_filter(valid_layers)

        if not selected:
            selected = fallback_filter(valid_layers)

        config = build_config(url, selected)
        final_config.extend(config)

    # deduplicate
    seen = set()
    deduped = []

    for c in final_config:
        key = (c["url"], tuple(c["type_names"]))
        if key not in seen:
            seen.add(key)
            deduped.append(c)

    with open(output_file, "w") as f:
        json.dump(deduped, f, indent=2)

    print(f"\n✅ Saved to {output_file}")


if __name__ == "__main__":
    generate_nrw_layers()