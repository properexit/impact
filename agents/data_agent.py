from tools.osm_tool import get_nearby_water

def data_agent(lat, lon):
    water = get_nearby_water(lat, lon)
    return {
        "water": water
    }