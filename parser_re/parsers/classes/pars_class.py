import requests
from bs4 import BeautifulSoup
import json
import re
import time

BASE_URL = "https://dnd.su"
START_URL = "https://dnd.su/class/"

headers = {
    "User-Agent": "Mozilla/5.0"
}


# =========================
# НОРМАЛИЗАЦИЯ
# =========================
def normalize_name(name):
    return name.lower().strip()


def split_features(text):
    return [f.strip() for f in text.split(",") if f.strip()]


# =========================
# ПАРСИНГ СПОСОБНОСТЕЙ ИЗ ТЕКСТА
# =========================
def extract_features_from_text(soup):
    features = {}

    for h in soup.select("h3, h4"):
        name = h.text.strip()

        content = []
        for sib in h.find_next_siblings():
            if sib.name in ["h3", "h4"]:
                break
            content.append(sib.get_text(" ", strip=True))

        description = "\n".join(content).strip()

        if name and description:
            features[normalize_name(name)] = {
                "name": name,
                "description": description
            }

    return features


# =========================
# СВЯЗКА С ТАБЛИЦЕЙ
# =========================
def enrich_table_with_descriptions(table, features_map):
    result = []

    for row in table:
        feature_names = split_features(row["features"])

        enriched_features = []

        for fname in feature_names:
            key = normalize_name(fname)

            if key in features_map:
                enriched_features.append(features_map[key])
            else:
                enriched_features.append({
                    "name": fname,
                    "description": None
                })

        result.append({
            "level": row["level"],
            "proficiency": row["proficiency"],
            "features": enriched_features
        })

    return result


# =========================
# ПАРСИНГ ОДНОГО КЛАССА
# =========================
def parse_class(url):
    print(f"Парсим: {url}")

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")

    data = {
        "id": url.rstrip("/").split("/")[-1],
        "url": url,
        "name": "",
        "name_en": "",
        "description": "",
        "levels": []
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

    # ===== ОПИСАНИЕ =====
    desc = soup.select_one(".desc")
    if desc:
        data["description"] = "\n".join(
            p.get_text(" ", strip=True)
            for p in desc.find_all("p")
        )

    # ===== ТАБЛИЦА =====
    table_data = []
    table = soup.select_one("table.class_table")

    if table:
        rows = table.find_all("tr")[1:]

        for row in rows:
            cols = [td.get_text(" ", strip=True) for td in row.find_all("td")]

            if len(cols) >= 3:
                table_data.append({
                    "level": cols[0],
                    "proficiency": cols[1],
                    "features": cols[2],
                    "extra": cols[3:]
                })

    # ===== СПОСОБНОСТИ =====
    features_map = extract_features_from_text(soup)

    # ===== СВЯЗКА =====
    data["levels"] = enrich_table_with_descriptions(
        table_data,
        features_map
    )

    return data


# =========================
# ПАРСИНГ СПИСКА КЛАССОВ
# =========================
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


# =========================
# ГЛАВНАЯ ФУНКЦИЯ
# =========================
def main():
    links = get_links_by_type("/class/")

    print(f"Найдено классов: {len(links)}")

    all_classes = []

    for link in links:
        try:
            data = parse_class(link)
            all_classes.append(data)

            time.sleep(0.5)  # чтобы не забанили

        except Exception as e:
            print(f"Ошибка: {link} -> {e}")

    with open("classes.json", "w", encoding="utf-8") as f:
        json.dump(all_classes, f, ensure_ascii=False, indent=2)

    print("Готово! Файл classes.json создан.")


if __name__ == "__main__":
    main()