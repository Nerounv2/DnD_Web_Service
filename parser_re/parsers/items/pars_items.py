import requests
from bs4 import BeautifulSoup
import json
import re
import time

BASE_URL = "https://dnd.su"
SITEMAP_URL = "https://dnd.su/sitemap.xml"

headers = {
    "User-Agent": "Mozilla/5.0"
}


# =========================
# ФИЛЬТР ССЫЛОК
# =========================
def is_valid_item(url):
    return bool(re.search(r"/items/\d+-", url))


# =========================
# ПОЛУЧАЕМ ВСЕ ССЫЛКИ
# =========================
def get_item_links():
    res = requests.get(SITEMAP_URL, headers=headers)
    soup = BeautifulSoup(res.text, "xml")

    links = set()

    for loc in soup.find_all("loc"):
        url = loc.text.strip()

        if "/items/" in url and is_valid_item(url):
            links.add(url)

    links = list(links)

    print(f"Найдено предметов (сырьё): {len(links)}")

    return links


# =========================
# META
# =========================
def parse_meta(soup):
    result: dict[str, str | None] = {
        "name_en": None,
        "rarity": None
    }

    meta = soup.find("meta", {"name": "description"})
    if not meta:
        return result

    content = meta.get("content", "")

    # English name
    match = re.search(r"\((.*?)\)", content)
    if match:
        result["name_en"] = match.group(1)

    # Rarity
    rarity_match = re.search(
        r"(обычного|необычного|редкого|очень редкого|легендарного)",
        content.lower()
    )
    if rarity_match:
        result["rarity"] = rarity_match.group(1)

    return result


# =========================
# ОПИСАНИЕ
# =========================
def parse_description(soup):
    desc = soup.select_one(".desc")

    if not desc:
        return ""

    return "\n".join(
        p.get_text(" ", strip=True)
        for p in desc.find_all("p")
    )


# =========================
# ЭФФЕКТЫ
# =========================
def parse_effects(soup):
    effects = []

    for h in soup.select("h3, h4"):
        name = h.get_text(strip=True)

        content = []
        for sib in h.find_next_siblings():
            if sib.name in ["h3", "h4"]:
                break
            content.append(sib.get_text(" ", strip=True))

        text = "\n".join(content).strip()

        if name and text:
            effects.append({
                "name": name,
                "description": text
            })

    return effects


# =========================
# ОДИН ПРЕДМЕТ
# =========================
def parse_item(url):
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return None

    soup = BeautifulSoup(res.text, "lxml")

    data = {
        "id": url.rstrip("/").split("/")[-1],
        "url": url,
        "name": "",
        "name_en": "",
        "category": "",
        "rarity": "",
        "description": "",
        "effects": []
    }

    # ===== НАЗВАНИЕ =====
    title = soup.select_one("h1.header-page_title")

    if not title:
        return None

    links = title.find_all("a")

    if len(links) >= 1:
        data["name"] = links[0].get_text(strip=True)

    if len(links) >= 2:
        data["category"] = links[1].get_text(strip=True)

    # ===== META =====
    meta = parse_meta(soup)
    data.update(meta)

    # ===== ОПИСАНИЕ =====
    data["description"] = parse_description(soup)

    # ===== ЭФФЕКТЫ =====
    data["effects"] = parse_effects(soup)

    # ❗ ФИЛЬТР ПУСТЫХ
    if not data["name"] or not data["description"]:
        return None

    return data


# =========================
# MAIN
# =========================
def main():
    links = get_item_links()

    items = []
    errors = 0

    for i, link in enumerate(links):
        try:
            item = parse_item(link)

            if item:
                print(f"Успешно спарсено: {i} -- {item['name']} ({link})")
                items.append(item)

            if i % 50 == 0:
                print(f"{i}/{len(links)}")

            # time.sleep(0.2)

        except Exception as e:
            errors += 1
            print(f"Ошибка: {link} -> {e}")

    print(f"\nГотово:")
    print(f"Всего валидных предметов: {len(items)}")
    print(f"Ошибок: {errors}")

    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()