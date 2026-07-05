import requests
from bs4 import BeautifulSoup
import json
import re
import time

BASE = "https://dnd.su"

# =========================
# UTILS
# =========================

def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_links(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()
    for a in soup.select("a"):
        href = str(a.get("href", ""))
        if "/feats/" in href and href != "/feats/":
            links.add(BASE + href)

    return list(links)

# =========================
# PARSE FEAT
# =========================

def parse_feat(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    span_title = soup.select_one("h2.card-title span[data-copy]")
    if not span_title:
        return None

    title_text = str(span_title.get("data-copy", ""))

    match = re.match(r"(.+?)\s*\[(.+?)\]", title_text)
    if match:
        name = match.group(1).strip()
        name_en = match.group(2).strip()
    else:
        name = title_text.strip()
        name_en = ""

    desc_p = soup.select_one("div.card__body p")
    description = desc_p.get_text(strip=True) if desc_p else ""

    props = [li.get_text(strip=True) for li in soup.select("div.card__body ul li")]

    return {
        "id": slug(name_en if name_en else name),
        "name": name,
        "name_en": name_en,
        "description": description,
        "properties": props
    }

# =========================
# NORMALIZER
# =========================


ABILITY_MAP = {
    "сил": "STR",
    "ловк": "DEX",
    "телос": "CON",
    "интел": "INT",
    "мудр": "WIS",
    "харизм": "CHA"
}

SKILL_MAP = {
    "атлетик": "athletics",
    "акробат": "acrobatics",
    "скрыт": "stealth",
    "вниман": "perception",
    "выступ": "performance",
    "обман": "deception",
    "прониц": "insight",
    "расслед": "investigation",
    "выживан": "survival",
    "маг": "arcana",
    "истор": "history",
    "природ": "nature",
    "религ": "religion",
    "убежден": "persuasion",
    "запуг": "intimidation",
    "ловкость рук": "sleight_of_hand",
    "уход за живот": "animal_handling",
    "медиц": "medicine"
}

def detect_abilities(text):
    found = []
    for k, v in ABILITY_MAP.items():
        if k in text:
            found.append(v)
    return list(set(found))


def detect_skills(text):
    found = []
    for k, v in SKILL_MAP.items():
        if k in text:
            found.append(v)
    return list(set(found))


def normalize_feat(feat):
    result = {
        "id": feat["id"],
        "name": feat["name"],
        "name_en": feat["name_en"],
        "description": feat["description"]
    }

    modifiers = {}
    flags = {}
    bonuses = {}
    proficiencies = {}
    choice = None
    uses = None

    for prop in feat["properties"]:
        p = prop.lower()

        # =========================
        # ABILITY BONUS / CHOICE
        # =========================
        match = re.search(r'увелич[^\d]+(\d)', p)
        if match:
            value = int(match.group(1))
            abilities = detect_abilities(p)

            if "или" in p and len(abilities) >= 2:
                choice = {
                    "type": "ability",
                    "choose": 1,
                    "options": abilities,
                    "value": value
                }
            elif abilities:
                for ab in abilities:
                    modifiers[ab] = modifiers.get(ab, 0) + value

        # =========================
        # SPEED
        # =========================
        match = re.search(r'скорость увеличивается на (\d+)', p)
        if match:
            modifiers["speed"] = int(match.group(1))

        # =========================
        # INITIATIVE
        # =========================
        match = re.search(r'\+(\d+) к инициативе', p)
        if match:
            modifiers["initiative"] = int(match.group(1))

        # =========================
        # HP PER LEVEL
        # =========================
        if "за каждый уровень" in p:
            match = re.search(r'(\d+)', p)
            if match:
                modifiers["hp_per_level"] = int(match.group(1))

        # =========================
        # SKILL PROFICIENCY
        # =========================
        if "владение" in p and "навык" in p:
            skills = detect_skills(p)

            match = re.search(r'(\d+)', p)
            if match:
                choice = {
                    "type": "skill",
                    "choose": int(match.group(1)),
                    "options": skills if skills else "any"
                }

        # =========================
        # SKILL ADVANTAGE
        # =========================
        if "преимущество" in p:
            skills = detect_skills(p)
            for s in skills:
                bonuses[f"skill:{s}"] = "advantage"

        # =========================
        # SAVING THROW PROFICIENCY
        # =========================
        if "спасброск" in p:
            abilities = detect_abilities(p)
            if abilities:
                proficiencies["saving_throws"] = abilities

        # =========================
        # REACTION
        # =========================
        if "реакци" in p:
            flags["has_reaction_effect"] = True

        # =========================
        # BONUS ACTION
        # =========================
        if "бонусным действием" in p:
            flags["has_bonus_action"] = True

        # =========================
        # SPECIFIC FLAGS
        # =========================
        if "не провоцируете атаки" in p:
            flags["no_opportunity_after_attack"] = True

        if "врасплох" in p:
            flags["no_surprise"] = True

        if "игнорируют укрытие" in p:
            flags["ignore_cover"] = True

        if "переброс" in p:
            flags["reroll"] = True

        if "дальность" in p and "помех" in p:
            flags["no_long_range_disadvantage"] = True

        # =========================
        # USES
        # =========================
        match = re.search(r'(\d+) очк', p)
        if match:
            uses = {
                "max": int(match.group(1)),
                "recharge": "long_rest"
            }

    # =========================
    # FINAL BUILD
    # =========================
    if modifiers:
        result["modifiers"] = modifiers
    if flags:
        result["flags"] = flags
    if bonuses:
        result["bonuses"] = bonuses
    if proficiencies:
        result["proficiencies"] = proficiencies
    if choice:
        result["choice"] = choice
    if uses:
        result["uses"] = uses

    return result
# =========================
# MAIN
# =========================

def main():
    links = get_links(BASE + "/feats/") + get_links(BASE + "/homebrew/feats/")
    links = list(set(links))

    print("Всего:", len(links))

    feats = []

    for i, link in enumerate(links):
        print(f"{i+1}/{len(links)}")

        try:
            raw = parse_feat(link)
            if raw:
                norm = normalize_feat(raw)
                feats.append(norm)
        except Exception as e:
            print("Ошибка:", e)

    with open("feats.json", "w", encoding="utf-8") as f:
        json.dump(feats, f, ensure_ascii=False, indent=2)

    print("ГОТОВО → feats.json")

if __name__ == "__main__":
    main()