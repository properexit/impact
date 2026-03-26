import requests
from config import LLM_BASE_URL, LLM_MODEL

def planner_agent(lat, lon):
    prompt = f"""
    A user selected location ({lat}, {lon}).
    What checks are needed for site due diligence?
    Keep it short.
    """

    response = requests.post(
        f"{LLM_BASE_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]