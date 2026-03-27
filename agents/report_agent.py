"""
Report agent — uses local Ollama (Mistral) to generate a structured
due diligence report from the aggregated JSONL feature data.

Expects Ollama running locally at http://localhost:11434
with the mistral model pulled: `ollama pull mistral`
"""

import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"


def load_data(path: str) -> list[dict]:
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return data


def build_context(data: list[dict]) -> dict:
    ctx = {
        "osm_features": {
            "natural": [],
            "waterway": [],
            "landuse": set(),
            "amenity": set(),
            "building_count": 0,
            "has_railway": False,
            "has_highway": False,
        },
        "flood_risk": None,
        "nrw_layers": {},
        "web_context": [],
        "web_snippets": [],
    }

    for d in data:
        dtype = d.get("type", "")

        if dtype not in ("flood_signal", "context_analysis") and not dtype.startswith("nrw_"):
            if d.get("natural"):
                ctx["osm_features"]["natural"].append(d["natural"])
            if d.get("waterway"):
                ctx["osm_features"]["waterway"].append(d["waterway"])
            if d.get("landuse"):
                ctx["osm_features"]["landuse"].add(d["landuse"])
            if d.get("amenity"):
                ctx["osm_features"]["amenity"].add(d["amenity"])
            if d.get("building"):
                ctx["osm_features"]["building_count"] += 1
            if d.get("highway"):
                ctx["osm_features"]["has_highway"] = True
            if d.get("railway"):
                ctx["osm_features"]["has_railway"] = True

        elif dtype == "flood_signal":
            ctx["flood_risk"] = d.get("flood_zone")

        elif dtype == "context_analysis":
            ctx["web_context"] = [x["name"] for x in d.get("developments", [])]
            ctx["web_snippets"] = d.get("snippets", [])

        elif dtype.startswith("nrw_"):
            label = d.get("label", dtype)
            ctx["nrw_layers"][label] = {
                "description": d.get("description", ""),
                "status": d.get("status", "unknown"),
                "count": d.get("count", 0),
                "features": d.get("features", [])[:3],
            }

    ctx["osm_features"]["landuse"] = list(ctx["osm_features"]["landuse"])
    ctx["osm_features"]["amenity"] = list(ctx["osm_features"]["amenity"])
    ctx["osm_features"]["natural"] = list(set(ctx["osm_features"]["natural"]))
    ctx["osm_features"]["waterway"] = list(set(ctx["osm_features"]["waterway"]))
    return ctx


REPORT_PROMPT_TEMPLATE = """You are a strict due diligence analyst.

Respond ONLY with valid JSON — no explanation, no markdown fences.

LOCATION: {location}
OSM FEATURES: {osm}
FLOOD RISK: {flood}
NRW WFS LAYERS: {nrw}
WEB CONTEXT: {web}

DERIVED SIGNALS (DO NOT IGNORE):
RISK_SCORE: {risk_score}
FLAGS: {flags}

STRICT RULES:
- You MUST respect the provided RISK_SCORE and FLAGS
- If FLAGS is non-empty → MUST describe risks clearly
- NEVER say "no risks" if FLAGS exist
- If RISK_SCORE >= 7 → recommendation must be cautious or restrictive
- Do NOT contradict the input signals

Respond with this exact JSON:
{{
  "risk_score": <integer 1-10>,
  "flags": ["<critical risk item>"],
  "warnings": ["<medium risk note>"],
  "sections": {{
    "location_overview": "<text>",
    "executive_summary": "<text>",
    "environmental_analysis": "<text>",
    "technical_analysis": "<text>",
    "risk_assessment": "<text>",
    "planning_context": "<text>",
    "recommendation": "<text>"
  }}
}}"""


def _call_ollama(prompt: str) -> str:
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2048,
                }
            },
            timeout=120,
        )
        if res.status_code != 200:
            raise RuntimeError(f"Ollama returned HTTP {res.status_code}")
        return res.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot connect to Ollama. Run: ollama serve")


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    text = re.sub(r"^```(?:json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from model output:\n{text[:500]}")


def generate_report(path: str, location_info: dict, risk_score: int, flags: list[str]) -> dict:
    data = load_data(path)
    context = build_context(data)

    nrw_summary = {
        k: {"status": v["status"], "count": v["count"], "desc": v["description"]}
        for k, v in context["nrw_layers"].items()
    }

    prompt = REPORT_PROMPT_TEMPLATE.format(
        location=json.dumps(location_info),
        osm=json.dumps(context["osm_features"]),
        flood=str(context["flood_risk"]),
        nrw=json.dumps(nrw_summary),
        web=json.dumps({
            "sources": context["web_context"][:5],
            "snippets": context["web_snippets"][:5],
        }),
        risk_score=risk_score,
        flags=json.dumps(flags),
    )

    try:
        raw = _call_ollama(prompt)
        report = _extract_json(raw)

        # 🔒 FORCE CONSISTENCY
        report["risk_score"] = risk_score
        report["flags"] = flags

        report.setdefault("warnings", [])
        report.setdefault("sections", {})

        for key in [
            "location_overview",
            "executive_summary",
            "environmental_analysis",
            "technical_analysis",
            "risk_assessment",
            "planning_context",
            "recommendation",
        ]:
            report["sections"].setdefault(key, "No data available.")

        report.setdefault("location", location_info)

        return report

    except Exception as e:
        print(f"⚠️ Ollama report generation failed: {e}")
        return _fallback_report(location_info, context, error=str(e))


def _fallback_report(location_info: dict, context: dict, error: str = "") -> dict:
    flags = []
    warnings = []
    risk = 3

    if context.get("flood_risk") is True:
        flags.append("Site intersects flood zone HQ100")
        risk += 3

    if context["nrw_layers"].get("protected_areas", {}).get("status") == "found":
        flags.append("Protected area (NSG/FFH/LSG) found in or near site")
        risk += 2

    if context["nrw_layers"].get("geology", {}).get("status") == "found":
        warnings.append("Geological data available — review foundation soil class")

    if context["nrw_layers"].get("water_bodies", {}).get("status") == "found":
        warnings.append("Water body detected within buffer — check distance and type")

    if error:
        warnings.append(f"Ollama unavailable: {error}")

    osm = context["osm_features"]

    return {
        "risk_score": min(risk, 10),
        "flags": flags,
        "warnings": warnings,
        "location": location_info,
        "sections": {
            "location_overview": (
                f"{location_info.get('city')}, {location_info.get('country')} "
                f"({location_info.get('latitude')}N, {location_info.get('longitude')}E)"
            ),
            "executive_summary": (
                f"{osm['building_count']} buildings detected. "
                f"Land uses: {', '.join(osm['landuse']) or 'none'}."
            ),
            "environmental_analysis": (
                f"Flood risk: {context['flood_risk']}. "
                f"Natural: {', '.join(osm['natural']) or 'none'}."
            ),
            "technical_analysis": f"{len(context['nrw_layers'])} NRW layers checked.",
            "risk_assessment": "\n".join(flags + warnings) or "No risks flagged.",
            "planning_context": (
                ", ".join(context["web_context"][:5])
                if context["web_context"] else "No web data."
            ),
            "recommendation": "Run Ollama for full AI analysis.",
        },
    }