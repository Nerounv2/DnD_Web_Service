import requests
from bs4 import BeautifulSoup
import json
import re

SITEMAP_URL = "https://dnd.su/sitemap.xml"


def get_links_by_type(path):
    res = requests.get(SITEMAP_URL)
    soup = BeautifulSoup(res.text, "xml")

    links = []

    for loc in soup.find_all("loc"):
        url = loc.text.strip()

        # только конечные страницы
        if path in url and re.search(r"/\d", url):
            links.append(url)

    return links


def parse_race(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")

    data = {
        "id": url.rstrip("/").split("/")[-1],
        "name": "",
        "name_en": "",
        "source": "",
        "description": "",
        "modifiers": {
            "stats": {},
            "speed": None,
            "fly_speed": None,
            "darkvision": None,
            "resistances": [],
            "abilities": []
        }
    }

    # ===== НАЗВАНИЕ =====
    title = soup.select_one("h2.card-title a.item-link")
    if title:
        full = title.text.strip()

        match = re.match(r"(.*?) \[(.*?)\]", full)
        if match:
            data["name"] = match.group(1)
            data["name_en"] = match.group(2)
        else:
            data["name"] = full

    # ===== ИСТОЧНИК =====
    source_elements = soup.find_all("strong")
    source = None
    for elem in source_elements:
        if re.search("Источник:", elem.text):
            source = elem
            break
    if source:
        span = source.find_next("span")
        if span:
            data["source"] = span.text.strip()

    # ===== ОПИСАНИЕ =====
    desc_block = soup.find("div", class_="desc")
    if desc_block:
        paragraphs = desc_block.find_all("p")
        data["description"] = "\n".join(p.text.strip() for p in paragraphs)

    # ===== ВЕСЬ ТЕКСТ (ВАЖНО!) =====
    full_text = soup.find("div", class_="card__body")
    text = full_text.get_text(" ", strip=True).lower() if full_text else ""

    # ===== СТАТЫ =====
    stats_map = {
        "сил": "str",
        "ловк": "dex",
        "телос": "con",
        "интел": "int",
        "мудр": "wis",
        "харизм": "cha"
    }

    for ru, key in stats_map.items():
        matches = re.findall(rf"{ru}\w* увеличивается на (\d+)", text)
        if matches:
            data["modifiers"]["stats"][key] = sum(map(int, matches))

    # ===== СКОРОСТЬ =====
    walk = re.search(r"скорость ходьбы[^\d]*(\d+)", text)
    if walk:
        data["modifiers"]["speed"] = int(walk.group(1))

    fly = re.search(r"скорость пол[её]та[^\d]*(\d+)", text)
    if fly:
        data["modifiers"]["fly_speed"] = int(fly.group(1))

    # ===== ТЁМНОЕ ЗРЕНИЕ =====
    dark = re.search(r"т[её]мное зрение[^\d]*(\d+)", text)
    if dark:
        data["modifiers"]["darkvision"] = int(dark.group(1))

    # ===== СОПРОТИВЛЕНИЯ =====
    resist = re.findall(r"сопротивление урону (\w+)", text)
    data["modifiers"]["resistances"] = list(set(resist))

    # ===== СПОСОБНОСТИ =====
    abilities_blocks = soup.find_all("h3")

    for h in abilities_blocks:
        name = h.text.strip()
        desc = []

        next_el = h.find_next_sibling()
        while next_el and next_el.name != "h3":
            desc.append(next_el.text.strip())
            next_el = next_el.find_next_sibling()

        if desc:
            data["modifiers"]["abilities"].append({
                "name": name,
                "effect": " ".join(desc)
            })

    return data


def main():
    links = links = get_links_by_type("/race/")
    print(f"Найдено рас: {len(links)}")

    all_data = []

    for link in links:
        print("Парсим:", link)
        try:
            race = parse_race(link)
            all_data.append(race)
        except Exception as e:
            print("Ошибка:", e)

    with open("races.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()