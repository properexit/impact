import requests
from config import LLM_BASE_URL, LLM_MODEL

def report_agent(lat, lon, risk_data):
    prompt = f"""
You are an expert urban planning and environmental consultant.

Generate a structured site due diligence report.

Location: ({lat}, {lon})

Findings:
{risk_data}

Structure:
1. Environmental Assessment
2. Technical Assessment
3. Key Risks
4. Recommendation

Keep it concise, professional, and decision-oriented.
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