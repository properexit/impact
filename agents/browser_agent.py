"""
Browser / web research agent.

Priority:
1. Brave Search API (if BRAVE_API_KEY is set) — structured JSON, reliable
2. DuckDuckGo HTML scrape — fallback, fragile but no key required
"""

import json
import os
import re
import requests
from typing import Callable


BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


def _brave_search(query: str, count: int = 5) -> list[dict]:
    """Search using Brave Search API. Returns list of {title, url, snippet}."""
    if not BRAVE_API_KEY:
        return []
    try:
        res = requests.get(
            BRAVE_URL,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={"q": query, "count": count, "lang": "de", "country": "de"},
            timeout=10,
        )
        if res.status_code != 200:
            return []
        data = res.json()
        results = []
        for r in data.get("web", {}).get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
            })
        return results
    except Exception:
        return []


def _ddg_search(query: str, count: int = 5) -> list[dict]:
    """DuckDuckGo search (fixed endpoint + parsing)."""
    try:
        from bs4 import BeautifulSoup

        res = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=12,
        )

        soup = BeautifulSoup(res.text, "html.parser")

        results = []

        for a in soup.select("a.result__a"):
            title = a.get_text(strip=True)
            url = a.get("href", "")

            # snippet (optional)
            parent = a.find_parent("div", class_="result")
            snippet = ""
            if parent:
                snip = parent.select_one(".result__snippet")
                if snip:
                    snippet = snip.get_text(strip=True)

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet[:200],
            })

            if len(results) >= count:
                break

        return results

    except Exception as e:
        print("DDG ERROR:", e)
        return []
def search(query: str, count: int = 5) -> list[dict]:
    """Search using best available method."""
    results = _brave_search(query, count)
    if not results:
        results = _ddg_search(query, count)
    return results


def deduplicate(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in results:
        key = r.get("url", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def run_browser_agent(
    city: str,
    country: str,
    lat: float,
    lon: float,
    zip_code: str | None = None,
    path: str = "data/site_features.jsonl",
    status_callback: Callable = print,
):
    """
    Run web research queries and append results to the JSONL store.
    Queries in both English and German to maximise NRW coverage.
    """
    zip_str = f" {zip_code}" if zip_code else ""
    loc = f"{city}{zip_str}, {country}"

    queries = [
        # German planning queries — highest signal for NRW sites
        f"Bebauungsplan {city}{zip_str}",
        f"Bauleitplanung {city} Flächennutzungsplan",
        f"Umweltbericht {city} Schutzgebiete",
        f"Kontaminierung Altlasten {city}{zip_str}",
        # English development context
        f"infrastructure projects near {lat:.3f} {lon:.3f}",
        f"urban development {city} {country}",
        f"real estate investment {city}",
    ]

    all_results = []
    for q in queries:
        status_callback(f"   🔎 Searching: {q}")
        results = search(q, count=4)
        status_callback(f"      → {len(results)} results")
        all_results.extend(results)

    unique = deduplicate(all_results)[:12]
    status_callback(f"   ✓ Web research: {len(unique)} unique results")

    record = {
        "type": "context_analysis",
        "location": loc,
        "coordinates": {"lat": lat, "lon": lon},
        "developments": [{"name": r["title"], "url": r["url"]} for r in unique],
        "snippets": [r.get("snippet", "") for r in unique if r.get("snippet")],
    }

    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")

    return unique