import json
import os


def load_rules(path="data/risk_rules.json"):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def evaluate_nrw(records, rules):
    score = 0
    flags = []

    for r in records:
        label = r.get("label")
        status = r.get("status")

        if status != "found":
            continue

        count = r.get("count", 0)
        features = r.get("features", [])

        layer_rules = rules.get(label, [])

        for rule in layer_rules:

            if "condition" in rule:
                condition = rule["condition"]

                try:
                    if eval(condition, {}, {"count": count}):  # ✅ FIXED
                        score += rule.get("score", 0)
                        flags.append(rule.get("flag"))
                except Exception:
                    continue

            # ✅ MATCH RULE (text-based)
            if "match" in rule:
                for f in features:
                    text = " ".join(str(v).lower() for v in f.values())
                    print(f"[DEBUG] Checking {label}: {text[:100]}")
                    
                    for keyword in rule["match"]:
                        if keyword in text:
                            print(f"[MATCH] {keyword} → +{rule.get('score')}")
                            score += rule.get("score", 0)
                            flags.append(rule.get("flag"))
                            break

    return score, flags