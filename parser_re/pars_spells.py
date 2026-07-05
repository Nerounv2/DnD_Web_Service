import requests
from bs4 import BeautifulSoup
import json
import re
import time

SITEMAP_URL = "https://dnd.su/sitemap.xml"

headers = {"User-Agent": "Mozilla/5.0"}


# =========================
# LINKS
# =========================
def get_spell_links():
    res = requests.get(SITEMAP_URL, headers=headers)
    soup = BeautifulSoup(res.text, "xml")

    links = []

    for loc in soup.find_all("loc"):
        url = loc.text.strip()

        if "/spells/" in url and re.search(r"/spells/\d+-", url):
            links.append(url)

    return links


# =========================
# PARSE SPELL
# =========================
def parse_spell(url):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "lxml")

    data = {
        "id": url.split("/")[-1],
        "url": url,
        "name": "",
        "name_en": "",
        "level": None,
        "school": "",
        "casting_time": "",
        "range": "",
        "components": "",
        "duration": "",
        "description": ""
    }

    # название
    title = soup.select_one("h2.card-title")
    if title:
        text = title.get_text(strip=True)

        # Fireball [Fireball]
        match = re.match(r"(.*?)\s*\[(.*?)\]", text)
        if match:
            data["name"] = match.group(1)
            data["name_en"] = match.group(2)

    # описание
    desc = soup.select_one(".desc")
    if desc:
        data["description"] = desc.get_text(" ", strip=True)

    # характеристики (лежат в списке)
    for li in soup.select(".card__body li"):
        t = li.get_text(" ", strip=True).lower()

        if "уровень" in t:
            lvl = re.search(r"\d+", t)
            if lvl:
                data["level"] = int(lvl.group())

        elif "школа" in t:
            data["school"] = t

        elif "время накладывания" in t:
            data["casting_time"] = t

        elif "дистанция" in t:
            data["range"] = t

        elif "компоненты" in t:
            data["components"] = t

        elif "длительность" in t:
            data["duration"] = t

    return data


# =========================
# MAIN
# =========================
def main():
    links = get_spell_links()
    print("Заклинаний найдено:", len(links))

    spells = []

    for i, link in enumerate(links):
        try:
            spells.append(parse_spell(link))
            print(f"Успешно спарсено: {i} -- {spells[-1]['name']} ({link})")
            
            if i % 50 == 0:
                
                print(i)

            # time.sleep(0.2)

        except Exception as e:
            print("Ошибка:", e)

    with open("spells.json", "w", encoding="utf-8") as f:
        json.dump(spells, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()