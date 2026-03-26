import json
import requests


def search_web(query):
    """
    Simple DuckDuckGo search (no API key needed)
    """
    url = "https://duckduckgo.com/html/"
    params = {"q": query}

    try:
        res = requests.post(url, data=params, timeout=10)
        text = res.text

        # very lightweight extraction (no bs4 to keep it simple)
        results = []

        for line in text.split("\n"):
            if "result__a" in line:
                start = line.find("href=\"") + 6
                end = line.find("\"", start)
                link = line[start:end]

                title_start = line.find(">") + 1
                title_end = line.find("</a>")
                title = line[title_start:title_end]

                results.append({
                    "title": title.strip(),
                    "url": link
                })

            if len(results) >= 5:
                break

        return results

    except Exception:
        return []


def run_browser_agent(city, country, lat, lon, path="data/site_features.jsonl"):
    print(f"📍 Location: {city}, {country} ({lat}, {lon})")

    queries = [
        f"infrastructure projects near {lat} {lon}",
        f"urban development {city}",
        f"construction projects {city}",
        f"real estate development {city}"
    ]

    all_results = []

    for q in queries:
        results = search_web(q)
        all_results.extend(results)

    # deduplicate by url
    seen = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)

    record = {
        "type": "context_analysis",
        "location": f"{city}, {country}",
        "coordinates": {
            "lat": lat,
            "lon": lon
        },
        "developments": [
            {"name": r["title"]} for r in unique_results[:5]
        ],
        "sources": unique_results[:5]
    }

    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"✅ Browser agent saved {len(unique_results[:5])} records")