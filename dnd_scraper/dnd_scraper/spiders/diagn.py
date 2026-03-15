import scrapy
import json
import re

class DiagnosticSpider(scrapy.Spider):
    name = "diagnostic"
    
    # Проверим все разделы
    sections = [
        {'name': 'spells', 'url': 'https://dnd.su/spells/', 'type': 'html'},
        {'name': 'spells_api', 'url': 'https://dnd.su/piece/spells/index-list/', 'type': 'api'},
        {'name': 'classes', 'url': 'https://dnd.su/class/', 'type': 'html'},
        {'name': 'races', 'url': 'https://dnd.su/race/', 'type': 'html'},
        {'name': 'feats', 'url': 'https://dnd.su/feats/', 'type': 'html'},
        {'name': 'feats_api', 'url': 'https://dnd.su/piece/feats/index-list/', 'type': 'api'},
        {'name': 'items', 'url': 'https://dnd.su/items/', 'type': 'html'},
        {'name': 'items_api', 'url': 'https://dnd.su/piece/items/index-list/', 'type': 'api'},
        {'name': 'bestiary', 'url': 'https://dnd.su/bestiary/', 'type': 'html'},
        {'name': 'bestiary_api', 'url': 'https://dnd.su/piece/bestiary/index-list/', 'type': 'api'},
        {'name': 'backgrounds', 'url': 'https://dnd.su/backgrounds/', 'type': 'html'},
    ]
    
    def start_requests(self):
        """Проверяем все URL"""
        for section in self.sections:
            yield scrapy.Request(
                url=section['url'],
                callback=self.parse_section,
                meta={'section': section},
                errback=self.handle_error,
                dont_filter=True
            )
    
    def parse_section(self, response):
        """Анализируем страницу раздела"""
        section = response.meta['section']
        
        print(f"\n{'='*60}")
        print(f"🔍 АНАЛИЗ РАЗДЕЛА: {section['name']}")
        print(f"📌 URL: {response.url}")
        print(f"📊 Статус: {response.status}")
        print(f"📦 Размер: {len(response.text)} байт")
        print(f"{'='*60}")
        
        # Сохраняем страницу для анализа
        filename = f"debug_{section['name']}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"💾 Страница сохранена в {filename}")
        
        # Проверяем наличие window.LIST (для API)
        if 'window.LIST' in response.text:
            print("✅ Найден window.LIST!")
            match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    items = data.get('cards', [])
                    print(f"   В нем {len(items)} элементов")
                    if len(items) > 0:
                        print(f"   Первый элемент: {items[0].get('title', 'No title')}")
                except:
                    print("   ❌ Но не смогли распарсить JSON")
        
        # Ищем элементы с data-id (для черт и предметов)
        data_ids = response.css('[data-id]')
        if data_ids:
            print(f"✅ Найдено элементов с data-id: {len(data_ids)}")
            # Покажем первые 3
            for i, elem in enumerate(data_ids[:3]):
                data_id = elem.attrib.get('data-id', '')
                data_source = elem.attrib.get('data-source', '')
                print(f"   {i+1}. ID: {data_id}, source: {data_source}")
        
        # Ищем все ссылки с href содержащим название раздела
        pattern = f"/{section['name'].replace('_api', '')}/"
        links = response.css(f'a[href*="{pattern}"]')
        if links:
            print(f"✅ Найдено ссылок на {pattern}: {len(links)}")
            for i, link in enumerate(links[:5]):
                href = link.attrib.get('href', '')
                text = link.css('::text').get()
                print(f"   {i+1}. {text} -> {href}")
        
        # Ищем плитки (для классов, рас)
        tiles = response.css('.tile, [class*="tile"]')
        if tiles:
            print(f"✅ Найдено плиток: {len(tiles)}")
        
        # Ищем элементы списка (для черт, предметов)
        list_items = response.css('.list-item, [class*="list-item"]')
        if list_items:
            print(f"✅ Найдено элементов списка: {len(list_items)}")
        
        # Если ничего не нашли, покажем структуру
        if not any([data_ids, links, tiles, list_items]):
            print("❌ Ничего не найдено стандартными селекторами!")
            print("\nПервые 1000 символов HTML:")
            print(response.text[:1000])
    
    def handle_error(self, failure):
        """Обрабатываем ошибки"""
        print(f"\n❌ Ошибка при загрузке {failure.request.url}")
        print(f"   Причина: {failure.value}")