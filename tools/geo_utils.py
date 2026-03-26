from geopy.geocoders import Nominatim

def get_bbox(polygon):
    return polygon.bounds



def get_location_name(lat, lon):
    try:
        geolocator = Nominatim(user_agent="geo_app")
        location = geolocator.reverse((lat, lon), language="en")

        address = location.raw.get("address", {})

        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("state")
        )

        country = address.get("country")

        return city, country

    except Exception:
        return "Unknown", "Unknown"