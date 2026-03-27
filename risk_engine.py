import json

def load_rules(path="risk_rules.json"):
    with open(path) as f:
        return json.load(f)


def evaluate_nrw(nrw_records, rules):
    risks = []
    score = 0

    for rec in nrw_records:
        if rec.get("status") != "found":
            continue

        for feature in rec.get("features", []):
            text = " ".join([str(v).lower() for v in feature.values() if v])
            
            for rule in rules.values():
                if any(k in text for k in rule["keywords"]):
                    risks.append(rule["message"])
                    score += rule["risk"]

    return score, list(set(risks))