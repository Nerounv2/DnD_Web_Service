import json
import re

def normalize_text(text):
    """Нормализует текст: убирает лишние пробелы и переносы строк."""
    if not text:
        return ""
    # Заменяем все пробельные символы (включая \n, \t, неразрывные пробелы) на один обычный пробел
    text = re.sub(r'\s+', ' ', text)
    # Убираем пробелы в начале и конце
    return text.strip()

# Пример исходных данных, которые получаем с сайта
raw_feats = [
    {
        "name": "Мастер средних доспехов",
        "name_en": "Medium armor master",
        "description": "Вы привыкли к перемещению в средних доспехах и получаете следующие преимущества:"
    },
    {
        "name": "Драконий кузнец",
        "name_en": "Dragonsmith",
        "description": "Вы обучились мастерствупревращения частей тела драконов в оружие и броню. Работая с оружейником или бронником, можно создавать оружие и броню из зубов, костей, чешуи, шкуры и других частей дракона."
    }
]

feats_json = []

for feat in raw_feats:
    name = normalize_text(feat.get("name"))
    name_en = normalize_text(feat.get("name_en"))
    description = normalize_text(feat.get("description"))

    # Генерация id из английского имени
    feat_id = re.sub(r'\s+', '-', name_en.lower())

    feats_json.append({
        "id": feat_id,
        "name": name,
        "name_en": name_en,
        "description": description
    })

# Сохраняем JSON в файл
with open("feats.json", "w", encoding="utf-8") as f:
    json.dump(feats_json, f, ensure_ascii=False, indent=4)

print("JSON успешно создан: feats.json")