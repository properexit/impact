import json
import requests


def load_data(path):
    data = []
    with open(path) as f:
        for line in f:
            data.append(json.loads(line))
    return data


def build_summary(data):
    summary = {
        "has_water": False,
        "landuse": set(),
        "amenities": set(),
        "buildings_count": 0,
        "has_flood_risk": None,
        "context_points": []
    }

    for d in data:
        if d.get("natural") == "water" or d.get("waterway"):
            summary["has_water"] = True

        if d.get("landuse"):
            summary["landuse"].add(d["landuse"])

        if d.get("amenity"):
            summary["amenities"].add(d["amenity"])

        if d.get("building"):
            summary["buildings_count"] += 1

        if d.get("flood_zone") is not None:
            summary["has_flood_risk"] = d["flood_zone"]

        if d.get("type") == "context_analysis":
            summary["context_points"] = [
                x["name"] for x in d.get("developments", [])
            ]

    summary["landuse"] = list(summary["landuse"])
    summary["amenities"] = list(summary["amenities"])

    return summary


def generate_report(path, location_info):
    data = load_data(path)
    summary = build_summary(data)

    prompt = f"""
You are a STRICT due diligence system.

LOCATION:
{location_info}

SUMMARY:
{summary}

Rules:
- Do NOT assume beyond data
- Do NOT speculate
- If data missing → say "No data available"
- Always include latitude and longitude in Location Overview

Generate:

0. Location Overview
1. Executive Summary
2. Environmental Analysis
3. Technical Analysis
4. Risk Assessment
5. Context Insights
6. Recommendation
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]