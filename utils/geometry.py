from shapely.geometry import Polygon

def load_polygon_from_json(data):
    coords = data["coordinates"]

    # Ensure polygon is closed
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    polygon = Polygon(coords)

    return polygon