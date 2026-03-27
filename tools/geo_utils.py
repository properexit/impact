from geopy.geocoders import Nominatim
from shapely.geometry import Polygon
import math


# NRW approximate bounding box
NRW_BOUNDS = {
    "min_lon": 5.85, "max_lon": 9.52,
    "min_lat": 50.32, "max_lat": 52.55,
}


def get_bbox(polygon: Polygon):
    """Returns (minx, miny, maxx, maxy)."""
    return polygon.bounds


def get_location_name(lat: float, lon: float):
    """Reverse geocode to city, country, zip."""
    try:
        geolocator = Nominatim(user_agent="geo_due_diligence_v2")
        location = geolocator.reverse((lat, lon), language="en", timeout=10)
        if not location:
            return "Unknown", "Unknown", None
        address = location.raw.get("address", {})
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("state")
        )
        country = address.get("country", "Unknown")
        zip_code = address.get("postcode")
        return city or "Unknown", country, zip_code
    except Exception:
        return "Unknown", "Unknown", None


def polygon_area_m2(polygon: Polygon) -> float:
    """Rough area in m² using equirectangular projection."""
    centroid_lat = polygon.centroid.y
    lat_m = 111_320.0
    lon_m = 111_320.0 * math.cos(math.radians(centroid_lat))
    coords = list(polygon.exterior.coords)
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i][0] * lon_m, coords[i][1] * lat_m
        x2, y2 = coords[i + 1][0] * lon_m, coords[i + 1][1] * lat_m
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def validate_nrw_bounds(lat: float, lon: float) -> bool:
    """Returns True if the point is within NRW's bounding box."""
    b = NRW_BOUNDS
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]


def bbox_with_buffer(polygon: Polygon, buffer_deg: float = 0.001):
    """Return bbox with a small buffer around the polygon."""
    minx, miny, maxx, maxy = polygon.bounds
    return minx - buffer_deg, miny - buffer_deg, maxx + buffer_deg, maxy + buffer_deg


def bbox_meters_buffer(polygon: Polygon, buffer_m: float = 100):
    """Return bbox buffered by N meters (approximate)."""
    buf_deg = buffer_m / 111_320.0
    return bbox_with_buffer(polygon, buf_deg)