import requests
import json
import re

url = 'https://dnd.su/piece/spells/index-list/'

print("Скачиваем данные о заклинаниях...")

try:
    # Скачиваем страницу
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    print(f"✅ Загружено {len(response.text)} байт")
    
    # Извлекаем JSON из <script>window.LIST = {...}</script>
    # Ищем паттерн: window.LIST = { ... };
    match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        print(f"✅ Найден JSON длиной {len(json_str)} символов")
        
        # Парсим JSON
        data = json.loads(json_str)
        spells = data.get('cards', [])
        
        print(f"\n🔥 ВСЕГО ЗАКЛИНАНИЙ: {len(spells)}")
        
        # Сохраняем в файл
        with open('spells.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✅ Данные сохранены в spells.json")
        
        # Покажем статистику
        levels = {}
        schools = {}
        
        for spell in spells[:10]:  # Первые 10 для проверки
            level = spell.get('level', 'unknown')
            school = spell.get('school', 'unknown')
            levels[level] = levels.get(level, 0) + 1
            schools[school] = schools.get(school, 0) + 1
        
        print("\n📊 Первые 10 заклинаний:")
        for i, spell in enumerate(spells[:10]):
            print(f"{i+1:2}. {spell.get('title'):25} | Уровень: {spell.get('level'):8} | Школа: {spell.get('school')}")
        
        print(f"\n📈 Всего заклинаний в файле: {len(spells)}")
        
    else:
        print("❌ Не удалось найти window.LIST в ответе")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")