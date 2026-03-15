import scrapy
import json
import re
from scrapy.http import Request

class ItemsSpider(scrapy.Spider):
    name = "items"
    
    allowed_domains = ["dnd.su"]
    
    def start_requests(self):
        """Начинаем с API endpoint для предметов"""
        api_url = 'https://dnd.su/piece/items/index-list/'
        print(f"\n{'='*60}")
        print(f"🔍 НАЧИНАЕМ ПАРСИНГ ПРЕДМЕТОВ")
        print(f"📡 API URL: {api_url}")
        print(f"{'='*60}\n")
        
        yield Request(
            url=api_url,
            callback=self.parse_api,
            errback=self.handle_error,
            dont_filter=True
        )
    
    def parse_api(self, response):
        """Парсим API ответ с предметами"""
        print(f"📥 Получен ответ от API")
        print(f"   Размер: {len(response.text)} байт")
        
        # Ищем window.LIST в ответе
        match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            
            try:
                data = json.loads(json_str)
                items = data.get('cards', [])
                
                print(f"✅ Найдено предметов: {len(items)}")
                
                # Словарь для типов предметов
                type_map = {
                    '1': 'Чудесный предмет',
                    '2': 'Зелье',
                    '3': 'Кольцо',
                    '4': 'Свиток',
                    '5': 'Волшебная палочка',
                    '6': 'Жезл',
                    '7': 'Посох',
                    '8': 'Доспех',
                    '9': 'Оружие',
                }
                
                # Словарь для редкости
                rarity_map = {
                    '1': 'Необычный',
                    '2': 'Редкий',
                    '3': 'Очень редкий',
                    '4': 'Легендарный',
                    '5': 'Редкость варьируется',
                    '6': 'Обычный',
                    '7': 'Артефакт',
                    '8': 'Не имеет редкости',
                }
                
                # Сохраняем список всех предметов
                items_list = []
                
                for i, item in enumerate(items, 1):
                    # Извлекаем основные поля
                    item_data = {
                        'id': item.get('id'),
                        'name': item.get('title'),
                        'name_en': item.get('title_en'),
                        'type_code': str(item.get('item_type', '')),
                        'rarity_code': str(item.get('quality', '')),
                        'url': f"https://dnd.su{item.get('link', '')}" if item.get('link') else '',
                        'attunement': item.get('attunement'),
                    }
                    
                    # Добавляем текстовые значения
                    item_data['type'] = type_map.get(item_data['type_code'], f'Unknown ({item_data["type_code"]})')
                    item_data['rarity'] = rarity_map.get(item_data['rarity_code'], f'Unknown ({item_data["rarity_code"]})')
                    
                    # Настройка (требуется/нет)
                    if item_data['attunement'] == 2:
                        item_data['attunement_text'] = 'Требуется настройка'
                    elif item_data['attunement'] == 1:
                        item_data['attunement_text'] = 'Не требуется настройка'
                    else:
                        item_data['attunement_text'] = 'Не указано'
                    
                    items_list.append(item_data)
                    
                    print(f"\n{i:3}. {item_data['name']}")
                    print(f"    Тип: {item_data['type']}")
                    print(f"    Редкость: {item_data['rarity']}")
                    print(f"    {item_data['attunement_text']}")
                    print(f"    Ссылка: {item_data['url']}")
                    
                    # Переходим на страницу предмета за подробностями
                    if item.get('link'):
                        yield Request(
                            url=f"https://dnd.su{item['link']}",
                            callback=self.parse_item_detail,
                            meta={'item': item_data},
                            dont_filter=True
                        )
                
                # Сохраняем список всех предметов
                with open('items_list.json', 'w', encoding='utf-8') as f:
                    json.dump(items_list, f, ensure_ascii=False, indent=2)
                
                print(f"\n{'='*60}")
                print(f"✅ ВСЕГО НАЙДЕНО ПРЕДМЕТОВ: {len(items_list)}")
                print(f"📁 Список сохранен в items_list.json")
                print(f"{'='*60}")
                
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка парсинга JSON: {e}")
                # Сохраняем для отладки
                with open('items_api_error.json', 'w', encoding='utf-8') as f:
                    f.write(json_str[:1000])
        else:
            print("❌ Не удалось найти window.LIST в ответе")
            print("Первые 500 символов ответа:")
            print(response.text[:500])
    
    def parse_item_detail(self, response):
        """Парсим детальную страницу предмета"""
        item = response.meta['item']
        
        print(f"\n📖 Детально: {item['name']}")
        print(f"   URL: {response.url}")
        
        # Ищем описание
        description = ''
        
        # Способ 1: entry-content
        content = response.css('div.entry-content')
        if content:
            paragraphs = content.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        # Способ 2: все параграфы
        if not description:
            paragraphs = response.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        # Ищем свойства предмета
        properties = {}
        
        # Часто свойства в таблице
        rows = response.css('tr')
        for row in rows:
            cells = row.css('td')
            if len(cells) >= 2:
                key = cells[0].css('::text').get()
                value = cells[1].css('::text').get()
                if key and value:
                    properties[key.strip()] = value.strip()
        
        # Добавляем информацию
        item['description'] = description[:5000] if description else ''
        item['properties'] = properties if properties else None
        item['detail_url'] = response.url
        
        print(f"   📝 Длина описания: {len(description)} символов")
        if properties:
            print(f"   📊 Найдено свойств: {len(properties)}")
        
        yield item
    
    def handle_error(self, failure):
        """Обрабатываем ошибки"""
        print(f"\n❌ Ошибка при загрузке: {failure.request.url}")
        print(f"   Причина: {failure.value}")
    
    def closed(self, reason):
        print(f"\n{'='*60}")
        print(f"✅ ПАРСИНГ ПРЕДМЕТОВ ЗАВЕРШЕН!")
        print(f"📊 Причина: {reason}")
        print(f"{'='*60}\n")