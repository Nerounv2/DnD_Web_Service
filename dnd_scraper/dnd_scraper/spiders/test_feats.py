import scrapy
import json
import re
from scrapy.http import Request

class UniversalDndSpider(scrapy.Spider):
    name = "universal_dnd"
    
    allowed_domains = ["dnd.su"]
    
    # ПОЛНАЯ КОНФИГУРАЦИЯ ДЛЯ ВСЕХ РАЗДЕЛОВ
    SECTIONS = {
        # ---------- API РАЗДЕЛЫ (ЗАГРУЖАЮТСЯ ЧЕРЕЗ window.LIST) ----------
        'spells': {
            'name': 'Заклинания',
            'list_type': 'api',
            'api_url': 'https://dnd.su/piece/spells/index-list/',
            'html_url': 'https://dnd.su/spells/',
            'output_dir': 'data/spells',
            'item_selector': '.cards_list__item a',
        },
        'items': {
            'name': 'Предметы',
            'list_type': 'api',
            'api_url': 'https://dnd.su/piece/items/index-list/',
            'html_url': 'https://dnd.su/items/',
            'output_dir': 'data/items',
            'item_selector': '.list-item__spell a',
        },
        'bestiary': {
            'name': 'Бестиарий',
            'list_type': 'api',
            'api_url': 'https://dnd.su/piece/bestiary/index-list/',
            'html_url': 'https://dnd.su/bestiary/',
            'output_dir': 'data/bestiary',
            'item_selector': '.cards_list__item a',
        },
        
        # ---------- HTML РАЗДЕЛЫ С ПЛИТКАМИ (КАК КЛАССЫ) ----------
        'classes': {
            'name': 'Классы',
            'list_type': 'tiles',
            'html_url': 'https://dnd.su/class/',
            'output_dir': 'data/classes',
            'tile_selector': '.tile a.tile-wrapper.class',
            'fields': {
                'name': '.article_title::text',
                'name_en': '.article_title_en::text',
                'source': '.article_source::text',
            },
        },
        'races': {
            'name': 'Расы',
            'list_type': 'tiles',
            'html_url': 'https://dnd.su/race/',
            'output_dir': 'data/races',
            'tile_selector': '.tile a.tile-wrapper.race',
            'fields': {
                'name': '.article_title::text',
                'name_en': '.article_title_en::text',
                'source': '.article_source::text',
            },
        },
        'backgrounds': {
            'name': 'Предыстории',
            'list_type': 'tiles',
            'html_url': 'https://dnd.su/backgrounds/',
            'output_dir': 'data/backgrounds',
            'tile_selector': '.tile a.tile-wrapper.background',
            'fields': {
                'name': '.article_title::text',
                'name_en': '.article_title_en::text',
                'source': '.article_source::text',
            },
        },
        
        # ---------- HTML РАЗДЕЛЫ СО СПИСКАМИ (КАК ЧЕРТЫ) ----------
        'feats': {
            'name': 'Черты',
            'list_type': 'list',
            'html_url': 'https://dnd.su/feats/',
            'output_dir': 'data/feats',
            'list_selector': 'div.col.list-item__spell.for_filter',
            'fields': {
                'name': 'a.list-item-wrapper div.list-item-title::text',
                'id': '@data-id',
                'source_code': '@data-source',
                'search_data': '@data-search',
            },
        },
    }
    
    # Словарь для кодов источников
    SOURCE_MAP = {
        '102': 'Player\'s Handbook',
        '101': 'Dungeon Master\'s Guide',
        '198': 'Bigby Presents: Glory of the Giants',
        '207': 'The Book of Many Things',
        '119': 'Eberron: Rising from the Last War',
        '152': 'Fizban\'s Treasury of Dragons',
        '205': 'Planescape: Adventures in the Multiverse',
        '108': 'Sword Coast Adventurer\'s Guide',
        '117': 'Tasha\'s Cauldron of Everything',
        '109': 'Xanathar\'s Guide to Everything',
        '183': 'Dragonlance: Shadow of the Dragon Queen',
        '155': 'Strixhaven: A Curriculum of Chaos',
    }
    
    def __init__(self, section='spells', *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if section not in self.SECTIONS:
            raise ValueError(f"Раздел должен быть одним из: {list(self.SECTIONS.keys())}")
        
        self.section = section
        self.config = self.SECTIONS[section]
        
        print(f"\n{'='*60}")
        print(f"🚀 ЗАПУСК ПАРСИНГА: {self.config['name']}")
        print(f"📁 Тип: {self.config['list_type']}")
        print(f"📂 Директория: {self.config['output_dir']}")
        print(f"{'='*60}\n")
    
    def start_requests(self):
        """Начинаем с правильного URL в зависимости от типа"""
        if self.config['list_type'] == 'api':
            yield Request(
                url=self.config['api_url'],
                callback=self.parse_api,
                errback=self.handle_error,
                dont_filter=True
            )
        else:
            yield Request(
                url=self.config['html_url'],
                callback=self.parse_html,
                errback=self.handle_error,
                dont_filter=True
            )
    
    def parse_api(self, response):
        """Парсим API ответ (для заклинаний, предметов, бестиария)"""
        print(f"\n📥 Получаем список {self.config['name']} через API...")
        
        match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            data = json.loads(json_str)
            items = data.get('cards', [])
            
            print(f"✅ Найдено {len(items)} {self.config['name']}")
            
            for i, item in enumerate(items, 1):
                # Базовые поля
                item_data = {
                    'id': item.get('id', i),
                    'name': item.get('title'),
                    'name_en': item.get('title_en'),
                    'url': f"https://dnd.su{item.get('link', '')}" if item.get('link') else '',
                }
                
                # Дополнительные поля для разных типов
                if self.section == 'items':
                    item_data.update({
                        'type': item.get('item_type'),
                        'rarity': item.get('quality'),
                        'attunement': item.get('attunement'),
                    })
                elif self.section == 'spells':
                    item_data.update({
                        'level': item.get('level'),
                        'school': item.get('school'),
                        'components': item.get('item_suffix'),
                        'concentration': 'concentration' in item.get('item_tags', {}),
                        'ritual': 'ritual' in item.get('item_tags', {}),
                    })
                
                print(f"  {i:3}. {item_data['name'][:40]}...")
                
                # Переходим на детальную страницу
                if item.get('link'):
                    yield Request(
                        url=f"https://dnd.su{item['link']}",
                        callback=self.parse_detail,
                        meta={'item': item_data},
                        dont_filter=True
                    )
        else:
            print("❌ API не сработал, пробуем HTML...")
            yield Request(
                url=self.config['html_url'],
                callback=self.parse_html,
                dont_filter=True
            )
    
    def parse_html(self, response):
        """Парсим HTML страницу"""
        print(f"\n📥 Парсим HTML {self.config['name']}...")
        
        items = []
        
        if self.config['list_type'] == 'tiles':
            # Для классов, рас, предысторий
            tiles = response.css(self.config['tile_selector'])
            print(f"Найдено плиток: {len(tiles)}")
            
            for tile in tiles:
                item = {
                    'url': response.urljoin(tile.attrib.get('href', '')),
                }
                for field, selector in self.config['fields'].items():
                    value = tile.css(selector).get()
                    if value:
                        item[field] = value.strip()
                items.append(item)
        
        elif self.config['list_type'] == 'list':
            # Для черт
            list_items = response.css(self.config['list_selector'])
            print(f"Найдено элементов списка: {len(list_items)}")
            
            for li in list_items:
                item = {
                    'id': li.attrib.get('data-id', ''),
                    'source_code': li.attrib.get('data-source', ''),
                    'search_data': li.attrib.get('data-search', ''),
                }
                
                # Извлекаем название и ссылку
                link = li.css('a.list-item-wrapper')
                if link:
                    item['url'] = response.urljoin(link.attrib.get('href', ''))
                    item['name'] = link.css('div.list-item-title::text').get()
                
                # Английское название из search_data
                if item.get('search_data') and ',' in item['search_data']:
                    parts = item['search_data'].split(',')
                    if len(parts) >= 2:
                        item['name_en'] = parts[1].strip().rstrip(',')
                
                # Источник
                item['source'] = self.SOURCE_MAP.get(item.get('source_code', ''), f'Unknown ({item.get("source_code", "")})')
                
                items.append(item)
        
        print(f"✅ Собрано {len(items)} {self.config['name']}")
        
        for item in items:
            yield Request(
                url=item['url'],
                callback=self.parse_detail,
                meta={'item': item},
                dont_filter=True
            )
    
    def parse_detail(self, response):
        """Парсим детальную страницу"""
        item = response.meta['item']
        
        print(f"\n📖 {item.get('name', 'Unknown')[:40]}...")
        
        # Ищем описание
        description = ''
        content = response.css('div.entry-content')
        if content:
            paragraphs = content.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        if not description:
            paragraphs = response.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        item['description'] = description[:5000]
        item['detail_url'] = response.url
        
        yield item
    
    def handle_error(self, failure):
        print(f"\n❌ Ошибка: {failure.request.url}")