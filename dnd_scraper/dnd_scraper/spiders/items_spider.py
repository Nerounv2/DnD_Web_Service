import scrapy
import re
from scrapy.http import Request

class ItemsFinalSpider(scrapy.Spider):
    name = "items_final"
    
    allowed_domains = ["dnd.su"]
    
    def start_requests(self):
        # Идем прямо на API endpoint
        url = 'https://dnd.su/piece/items/index-list/'
        print(f"\n{'='*60}")
        print(f"🔍 ПАРСИНГ ПРЕДМЕТОВ ЧЕРЕЗ API")
        print(f"URL: {url}")
        print(f"{'='*60}\n")
        
        yield Request(
            url=url,
            callback=self.parse_api,
            dont_filter=True
        )
    
    def parse_api(self, response):
        print(f"Статус: {response.status}")
        print(f"Размер ответа: {len(response.text)} байт")
        
        # Сохраняем для анализа
        with open('items_api_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("✅ API ответ сохранен в items_api_debug.html")
        
        # Находим все предметы в HTML
        # Они выглядят так:
        # <div class='col list-item__spell for_filter' data-search='...' data-id='2337'>
        items = response.css('div.col.list-item__spell.for_filter')
        print(f"\n✅ Найдено предметов в HTML: {len(items)}")
        
        if len(items) == 0:
            print("❌ Предметы не найдены! Проверяем структуру...")
            # Попробуем другие селекторы
            items = response.css('.list-item__spell')
            print(f"   По классу .list-item__spell: {len(items)}")
        
        # Словарь для редкости
        rarity_map = {
            'quality_color-1': 'Необычный',
            'quality_color-2': 'Редкий',
            'quality_color-3': 'Очень редкий',
            'quality_color-4': 'Легендарный',
            'quality_color-5': 'Редкость варьируется',
            'quality_color-6': 'Обычный',
            'quality_color-7': 'Артефакт',
        }
        
        # Типы предметов
        type_map = {
            'item_type_magic': 'Чудесный предмет',
            'item_type_potion': 'Зелье',
            'item_type_ring': 'Кольцо',
            'item_type_scroll': 'Свиток',
            'item_type_wand': 'Волшебная палочка',
            'item_type_rod': 'Жезл',
            'item_type_staff': 'Посох',
            'item_type_armor': 'Доспех',
            'item_type_weapon': 'Оружие',
        }
        
        for i, item in enumerate(items, 1):
            # Основные атрибуты
            data_id = item.attrib.get('data-id', '')
            data_search = item.attrib.get('data-search', '')
            
            # Ссылка и название
            link = item.css('a.list-item-wrapper')
            if link:
                href = link.attrib.get('href', '')
                
                # Название
                name = link.css('span.list-item-title::text').get()
                
                # Тип предмета (из иконки)
                icon = link.css('span[class*="list-svg__"]')
                icon_class = ''
                if icon:
                    for cls in icon.attrib.get('class', '').split():
                        if 'list-svg__' in cls:
                            icon_class = cls.replace('list-svg__', '')
                            break
                item_type = type_map.get(icon_class, 'Чудесный предмет')
                
                # Редкость
                quality = link.css('span[class*="quality_color"]')
                rarity_class = ''
                if quality:
                    for cls in quality.attrib.get('class', '').split():
                        if 'quality_color' in cls:
                            rarity_class = cls
                            break
                rarity = rarity_map.get(rarity_class, 'Неизвестно')
                
                # Настройка
                attunement = link.css('span.list-icon__set').get() is not None
                
                # Английское название
                name_en = ''
                if data_search and ',' in data_search:
                    parts = data_search.split(',')
                    if len(parts) >= 2:
                        name_en = parts[1].strip().rstrip(',')
                
                item_data = {
                    'id': data_id,
                    'name': name.strip() if name else '',
                    'name_en': name_en,
                    'type': item_type,
                    'rarity': rarity,
                    'attunement': attunement,
                    'url': f"https://dnd.su{href}" if href else '',
                }
                
                print(f"\n{i:3}. {item_data['name']}")
                print(f"    Тип: {item_data['type']}")
                print(f"    Редкость: {item_data['rarity']}")
                print(f"    Настройка: {'Да' if item_data['attunement'] else 'Нет'}")
                print(f"    ID: {item_data['id']}")
                
                # Переходим на детальную страницу
                if href:
                    yield Request(
                        url=f"https://dnd.su{href}",
                        callback=self.parse_detail,
                        meta={'item': item_data},
                        dont_filter=True
                    )
        
        print(f"\n{'='*60}")
        print(f"✅ ВСЕГО НАЙДЕНО ПРЕДМЕТОВ: {len(items)}")
        print(f"{'='*60}")
    
    def parse_detail(self, response):
        """Парсим детальную страницу предмета"""
        item = response.meta['item']
        
        print(f"\n📖 Детально: {item['name']}")
        
        # Ищем описание
        description = ''
        
        # Основной контент
        content = response.css('div.entry-content')
        if content:
            paragraphs = content.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        # Если не нашли, берем все параграфы
        if not description:
            paragraphs = response.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        # Ищем свойства в таблице
        properties = {}
        rows = response.css('tr')
        for row in rows:
            cells = row.css('td')
            if len(cells) >= 2:
                key = cells[0].css('::text').get()
                value = cells[1].css('::text').get()
                if key and value:
                    properties[key.strip()] = value.strip()
        
        item['description'] = description[:5000] if description else ''
        item['properties'] = properties if properties else None
        item['detail_url'] = response.url
        
        print(f"   📝 Длина описания: {len(description)} символов")
        if properties:
            print(f"   📊 Найдено свойств: {len(properties)}")
        
        yield item