import re
import json


def extract_dice(text):
    match = re.search(r"\d+к\d+", text.lower())
    return match.group(0) if match else None

def extract_range(text):
    match = re.search(r"(\d+)\s*фут", text.lower())
    return int(match.group(1)) if match else None

def detect_type(text):
    if not text:
        return "passive"

    text = text.lower()

    if "бонусным действием" in text:
        return "bonus_action"
    if "реакцией" in text:
        return "reaction"
    if "действием" in text:
        return "action"

    return "passive"

def extract_uses(text):
    text = text.lower()

    if "равное вашему бонусу мастерства" in text:
        return "proficiency_bonus"

    if "равное модификатору" in text:
        return "ability_modifier"

    return None

def extract_recharge(text):
    text = text.lower()

    if "продолжительного отдыха" in text:
        return "long_rest"
    if "короткого отдыха" in text:
        return "short_rest"

    return None

def normalize_feature(feature):
    text = feature.get("description") or ""

    return {
        "name": feature.get("name"),
        "type": detect_type(text),
        "dice": extract_dice(text),
        "range": extract_range(text),
        "uses": extract_uses(text),
        "recharge": extract_recharge(text),
        "description": text
    }

def normalize_classes(data):
    for cls in data:
        for lvl in cls["levels"]:
            new_features = []

            for f in lvl["features"]:
                new_features.append(normalize_feature(f))

            lvl["features"] = new_features

    return data

def main():
    with open("classes.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    data = normalize_classes(data)

    with open("classes_normalized.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Готово!")

if __name__ == "__main__":
    main()