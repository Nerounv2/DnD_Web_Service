import json
import re


def extract_size(text):
    match = re.search(r"размер[^\w]*(маленький|средний|большой)", text)
    if match:
        return match.group(1)
    return None


def extract_speeds(text) -> dict[str, int | None]:
    speeds: dict[str, int | None] = {
        "walk": None,
        "fly": None,
        "climb": None,
        "swim": None
    }

    walk = re.search(r"скорость ходьбы[^\d]*(\d+)", text)
    fly = re.search(r"скорость пол[её]та[^\d]*(\d+)", text)
    climb = re.search(r"скорость лазания[^\d]*(\d+)", text)
    swim = re.search(r"скорость плавания[^\d]*(\d+)", text)

    if walk:
        speeds["walk"] = int(walk.group(1))
    if fly:
        speeds["fly"] = int(fly.group(1))
    if climb:
        speeds["climb"] = int(climb.group(1))
    if swim:
        speeds["swim"] = int(swim.group(1))

    return speeds


def extract_darkvision(text):
    match = re.search(r"т[её]мное зрение[^\d]*(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def extract_resistances(text):
    matches = re.findall(r"сопротивление урону (\w+)", text)
    return list(set(matches))


def extract_stats(text):
    stats = {
        "str": 0,
        "dex": 0,
        "con": 0,
        "int": 0,
        "wis": 0,
        "cha": 0
    }

    mapping = {
        "сил": "str",
        "ловк": "dex",
        "телос": "con",
        "интел": "int",
        "мудр": "wis",
        "харизм": "cha"
    }

    for ru, key in mapping.items():
        matches = re.findall(rf"{ru}\w* увеличивается на (\d+)", text)
        if matches:
            stats[key] += sum(map(int, matches))

    return stats


def extract_languages(text):
    match = re.search(r"говорить.*?на ([^\.]+)", text)
    if match:
        langs = match.group(1)
        return [l.strip() for l in re.split(r",| и ", langs)]
    return []


def normalize_race(race):
    full_text = (race.get("description", "") + " " +
                 " ".join([a.get("effect", "") for a in race["modifiers"].get("abilities", [])])
                 ).lower()

    normalized = {
        "id": race.get("id"),
        "name": race.get("name"),
        "name_en": race.get("name_en"),
        "source": race.get("source"),
        "description": race.get("description"),

        "size": extract_size(full_text),

        "speed": extract_speeds(full_text),

        "stats": extract_stats(full_text),

        "vision": {
            "darkvision": extract_darkvision(full_text)
        },

        "resistances": extract_resistances(full_text),

        "languages": extract_languages(full_text),

        "traits": race["modifiers"].get("abilities", [])
    }

    return normalized


def main():
    with open("races.json", "r", encoding="utf-8") as f:
        races = json.load(f)

    clean = []

    for race in races:
        try:
            normalized = normalize_race(race)
            clean.append(normalized)
        except Exception as e:
            print("Ошибка:", race.get("name"), e)

    with open("races_clean.json", "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=4)

    print(f"Готово! Обработано рас: {len(clean)}")


if __name__ == "__main__":
    main()