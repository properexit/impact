import requests
import xml.etree.ElementTree as ET
from io import BytesIO
import geopandas as gpd


def get_feature_types(wfs_url):
    url = f"{wfs_url}?service=WFS&request=GetCapabilities"
    print(f"\n📡 Fetching capabilities: {wfs_url}")

    try:
        res = requests.get(url, timeout=20)

        if res.status_code != 200:
            print("❌ Failed request")
            return []

        root = ET.fromstring(res.content)

        feature_types = []

        # ✅ namespace-agnostic search
        for elem in root.iter():
            if elem.tag.endswith("FeatureType"):
                for child in elem:
                    if child.tag.endswith("Name"):
                        feature_types.append(child.text)

        return feature_types

    except Exception as e:
        print(f"❌ Error parsing XML: {e}")
        return []
    
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

        print(f"   → {typename} | status={res.status_code} size={len(res.content)}")

        if res.status_code != 200 or len(res.content) < 200:
            return False

        gdf = gpd.read_file(BytesIO(res.content))

        return gdf is not None and not gdf.empty

    except Exception as e:
        print(f"   ⚠️ {typename} failed: {e}")
        return False


def discover_wfs_layers(wfs_url):
    feature_types = get_feature_types(wfs_url)

    print(f"\n🔍 Found {len(feature_types)} feature types")

    working = []

    for t in feature_types[:20]:  # limit for testing
        print(f"\nTesting: {t}")

        if test_typename(wfs_url, t):
            print(f"   ✅ WORKS: {t}")
            working.append(t)
        else:
            print(f"   ❌ FAIL")

    return working


if __name__ == "__main__":
    urls = [
        "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_aaa-modell-basiert",
    ]

    for url in urls:
        working = discover_wfs_layers(url)

        print("\n✅ FINAL WORKING TYPES:")
        for w in working:
            print(f"  - {w}")