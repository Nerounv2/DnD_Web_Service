import json
import re


# =========================
# УТИЛИТЫ
# =========================
def text_all(item):
    parts = [item.get("description", "")]
    parts += [e.get("description", "") for e in item.get("effects", [])]
    return " ".join(parts).lower()


# =========================
# RARITY NORMALIZE
# =========================
def normalize_rarity(text):
    if not text:
        return None

    text = text.lower()

    if "обыч" in text:
        return "common"
    if "необыч" in text:
        return "uncommon"
    if "редк" in text and "очень" not in text:
        return "rare"
    if "очень редк" in text:
        return "very_rare"
    if "легендар" in text:
        return "legendary"

    return None


# =========================
# TYPE
# =========================
def detect_type(text):
    if "оружие" in text:
        return "weapon"
    if "доспех" in text or "кд" in text:
        return "armor"
    if "зелье" in text:
        return "potion"
    if "кольцо" in text:
        return "ring"
    if "жезл" in text:
        return "wand"
    if "посох" in text:
        return "staff"

    return "wondrous"


# =========================
# ATTUNEMENT
# =========================
def detect_attunement(text):
    return "настройк" in text


# =========================
# MODIFIERS
# =========================
def get_bonus(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


def parse_modifiers(text):
    return {
        "ac_bonus": get_bonus(r"\+(\d+)\s*к\s*кд", text),
        "attack_bonus": get_bonus(r"\+(\d+)\s*к\s*броскам атаки", text),
        "damage_bonus": get_bonus(r"\+(\d+)\s*к\s*урону", text),
        "spell_attack_bonus": get_bonus(r"\+(\d+)\s*к\s*атакам заклинаниями", text),
        "spell_dc_bonus": get_bonus(r"\+(\d+)\s*к\s*сл спасброска", text)
    }


# =========================
# DAMAGE
# =========================
def parse_damage(text):
    match = re.search(r"(\d+d\d+)", text)

    if not match:
        return None

    dmg_type = None

    types = {
        "рубящ": "slashing",
        "колющ": "piercing",
        "дробящ": "bludgeoning",
        "огнен": "fire",
        "холод": "cold",
        "молни": "lightning",
        "некрот": "necrotic",
        "псих": "psychic"
    }

    for k, v in types.items():
        if k in text:
            dmg_type = v

    return {
        "dice": match.group(1),
        "type": dmg_type
    }


# =========================
# CHARGES
# =========================
def parse_charges(text):
    m = re.search(r"(\d+)\s*заряд", text)
    if not m:
        return None

    recharge = None
    if "рассвет" in text:
        recharge = "dawn"
    elif "закат" in text:
        recharge = "dusk"
    elif "короткого отдыха" in text:
        recharge = "short_rest"
    elif "длительного отдыха" in text:
        recharge = "long_rest"

    return {
        "max": int(m.group(1)),
        "recharge": recharge
    }


# =========================
# ЭФФЕКТЫ (умнее)
# =========================
def normalize_effects(item):
    result = []

    for e in item.get("effects", []):
        text = (e.get("description") or "").lower()

        effect_type = "passive"

        if "действием" in text:
            effect_type = "action"
        elif "бонусным действием" in text:
            effect_type = "bonus_action"
        elif "реакцией" in text:
            effect_type = "reaction"

        result.append({
            "name": e.get("name"),
            "type": effect_type
        })

    return result


# =========================
# MAIN NORMALIZE
# =========================
def normalize_item(item):
    text = text_all(item)

    return {
        **item,

        "rarity": normalize_rarity(item.get("rarity")),
        "type": detect_type(text),
        "attunement": detect_attunement(text),

        "modifiers": parse_modifiers(text),
        "damage": parse_damage(text),
        "charges": parse_charges(text),

        "effects": normalize_effects(item)
    }


# =========================
# MAIN
# =========================
def main():
    with open("items.json", "r", encoding="utf-8") as f:
        items = json.load(f)

    result = [normalize_item(i) for i in items]

    with open("items_final.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("🔥 items_final.json готов")


if __name__ == "__main__":
    main()