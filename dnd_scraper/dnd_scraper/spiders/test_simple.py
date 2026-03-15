import scrapy
import json
import re
import os
from datetime import datetime
from scrapy.http import Request

class UniversalDndSpider(scrapy.Spider):
    name = "universal_dnd"
    
    allowed_domains = ["dnd.su"]
    
    # Конфигурация для разделов
    SECTIONS = {
        'spells': {
            'name': 'Заклинания',
            'name_en': 'spells',
            'list_url': 'https://dnd.su/spells/',
            'list_type': 'api',
            'data_endpoint': '/piece/spells/index-list/',
            'item_pattern': r'/spells/[\w-]+/',
            'item_selector': '.cards_list__item a',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.entry-content p::text',
            'output_dir': 'data/spells'
        },
        'classes': {
            'name': 'Классы',
            'name_en': 'classes',
            'list_url': 'https://dnd.su/class/',
            'list_type': 'html',
            'item_selector': '.tile a.tile-wrapper.class',
            'fields': {
                'name': '.article_title::text',
                'name_en': '.article_title_en::text',
                'source': '.article_source::text',
                'icon': '.tile__icon[class*="sprite-class__"]::attr(class)',
            },
            'item_pattern': r'/class/[\w-]+/',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.class-description p::text, div.entry-content p::text',
            'output_dir': 'data/classes'
        },
        'races': {
            'name': 'Расы',
            'name_en': 'races',
            'list_url': 'https://dnd.su/race/',
            'list_type': 'html',
            'item_selector': '.tile a.tile-wrapper.race',
            'fields': {
                'name': '.article_title::text',
                'name_en': '.article_title_en::text',
                'source': '.article_source::text',
                'icon': '.tile__icon[class*="sprite-race__"]::attr(class)',
            },
            'item_pattern': r'/race/[\w-]+/',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.race-description p::text, div.entry-content p::text',
            'output_dir': 'data/races'
        },
        'feats': {
            'name': 'Черты',
            'name_en': 'feats',
            'list_url': 'https://dnd.su/feats/',
            'list_type': 'html',
            # Черты находятся в div с классом grid-4_lg-3_md-2_xs-1 list index-settings
            'item_selector': '.list-item__spell a.list-item-wrapper',
            'fields': {
                'name': '.list-item-title::text',
                'source': 'ancestor::div[contains(@class, "list-item__spell")]/@data-source',
                'id': 'ancestor::div[contains(@class, "list-item__spell")]/@data-id',
                'search_data': 'ancestor::div[contains(@class, "list-item__spell")]/@data-search',
            },
            'item_pattern': r'/feats/[\w-]+/',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.feat-description p::text, div.entry-content p::text',
            'output_dir': 'data/feats'
        },
        'items': {
            'name': 'Предметы',
            'name_en': 'items',
            'list_url': 'https://dnd.su/items/',
            'list_type': 'html',
            'item_selector': '.tile a.tile-wrapper.item',
            'fields': {
                'name': '.article_title::text',
                'source': '.article_source::text',
            },
            'item_pattern': r'/items/[\w-]+/',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.item-description p::text, div.entry-content p::text',
            'output_dir': 'data/items'
        },
        'bestiary': {
            'name': 'Бестиарий',
            'name_en': 'bestiary',
            'list_url': 'https://dnd.su/bestiary/',
            'list_type': 'api',
            'data_endpoint': '/piece/bestiary/index-list/',
            'item_pattern': r'/bestiary/[\w-]+/',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.bestiary-description p::text, div.entry-content p::text',
            'output_dir': 'data/bestiary'
        },
        'backgrounds': {
            'name': 'Предыстории',
            'name_en': 'backgrounds',
            'list_url': 'https://dnd.su/backgrounds/',
            'list_type': 'html',
            'item_selector': '.tile a.tile-wrapper.background',
            'fields': {
                'name': '.article_title::text',
                'source': '.article_source::text',
            },
            'item_pattern': r'/backgrounds/[\w-]+/',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.background-description p::text, div.entry-content p::text',
            'output_dir': 'data/backgrounds'
        }
    }
    
    def __init__(self, section='spells', *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if section not in self.SECTIONS:
            raise ValueError(f"Раздел должен быть одним из: {list(self.SECTIONS.keys())}")
        
        self.section = section
        self.config = self.SECTIONS[section]
        
        # Создаем директорию для данных
        self.output_dir = self.config['output_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Файлы для разных типов данных
        self.files = {
            'list': f"{self.output_dir}/list.json",
            'details': f"{self.output_dir}/details.json",
            'summary': f"{self.output_dir}/summary.json",
            'errors': f"{self.output_dir}/errors.json",
            'stats': f"{self.output_dir}/stats.json",
        }
        
        # Данные
        self.items_list = []
        self.details = []
        self.errors = []
        self.stats = {
            'section': self.config['name'],
            'start_time': datetime.now().isoformat(),
            'total_found': 0,
            'processed': 0,
            'failed': 0,
            'sources': {},
            'types': {}
        }
        
        # Для отслеживания прогресса
        self.processed_urls = set()
        
        print(f"\n{'='*60}")
        print(f"🚀 ЗАПУСК ПАРСИНГА: {self.config['name']}")
        print(f"📁 Режим: {self.config['list_type']}")
        print(f"📂 Директория: {self.output_dir}")
        print(f"{'='*60}\n")
    
    def start_requests(self):
        """Начинаем с получения списка"""
        if self.config['list_type'] == 'api':
            endpoint = f"https://dnd.su{self.config['data_endpoint']}"
            yield Request(
                url=endpoint,
                callback=self.parse_api_list,
                errback=self.handle_error,
                dont_filter=True
            )
        else:
            yield Request(
                url=self.config['list_url'],
                callback=self.parse_html_list,
                errback=self.handle_error,
                dont_filter=True
            )
    
    def parse_api_list(self, response):
        """Парсим список из API"""
        print(f"\n📥 Получаем список {self.config['name']} через API...")
        
        match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            data = json.loads(json_str)
            items = data.get('cards', [])
            
            self.stats['total_found'] = len(items)
            print(f"✅ Найдено {self.stats['total_found']} {self.config['name']}")
            
            # Сохраняем список
            self.items_list = items
            self.save_json(self.files['list'], items)
            
            # Считаем статистику по источникам
            for item in items:
                sources = item.get('filter_source', [])
                for source in sources:
                    self.stats['sources'][str(source)] = self.stats['sources'].get(str(source), 0) + 1
            
            self.save_stats()
            
            # Создаем запросы для каждого элемента
            for i, item in enumerate(items, 1):
                if 'link' in item:
                    url = f"https://dnd.su{item['link']}"
                    
                    if i % 50 == 0 or i == 1:
                        print(f"  ⏳ Добавлено в очередь: {i}/{self.stats['total_found']}")
                    
                    yield Request(
                        url=url,
                        callback=self.parse_detail,
                        errback=self.handle_error,
                        meta={'item': item, 'index': i},
                        dont_filter=True
                    )
            
            print(f"\n✅ Все {self.stats['total_found']} {self.config['name']} добавлены в очередь!")
        else:
            print("❌ API не сработал, пробуем HTML...")
            yield Request(
                url=self.config['list_url'],
                callback=self.parse_html_list,
                errback=self.handle_error,
                dont_filter=True
            )
    
    def parse_html_list(self, response):
        """Парсим список из HTML"""
        print(f"\n📥 Парсим HTML список {self.config['name']}...")
        
        items = []
        selector = self.config.get('item_selector')
        
        if selector:
            elements = response.css(selector)
            print(f"Найдено элементов по селектору: {len(elements)}")
            
            for elem in elements:
                item = {
                    'url': response.urljoin(elem.attrib.get('href', '')),
                }
                
                fields = self.config.get('fields', {})
                for field_name, field_selector in fields.items():
                    value = elem.css(field_selector).get()
                    if value:
                        item[field_name] = value.strip()
                
                # Извлекаем иконку
                if 'icon' in item:
                    icon_match = re.search(r'sprite-(?:class|race)__(\w+)', item['icon'])
                    if icon_match:
                        item['icon_name'] = icon_match.group(1)
                
                items.append(item)
                
                # Считаем источники
                source = item.get('source', 'Unknown')
                self.stats['sources'][source] = self.stats['sources'].get(source, 0) + 1
            
            self.stats['total_found'] = len(items)
            print(f"✅ Найдено {self.stats['total_found']} {self.config['name']}")
            
            # Сохраняем список
            self.items_list = items
            self.save_json(self.files['list'], items)
            self.save_stats()
            
            # Создаем запросы
            for i, item in enumerate(items, 1):
                if i % 5 == 0 or i == 1:
                    print(f"  ⏳ Добавлено в очередь: {i}/{self.stats['total_found']}")
                
                yield Request(
                    url=item['url'],
                    callback=self.parse_detail,
                    errback=self.handle_error,
                    meta={'item': item, 'index': i},
                    dont_filter=True
                )
            
            print(f"\n✅ Все {self.stats['total_found']} {self.config['name']} добавлены в очередь!")
    
    def parse_detail(self, response):
        """Парсим детальную страницу"""
        item = response.meta['item'].copy()
        index = response.meta.get('index', 0)
        
        # Добавляем URL
        item['url'] = response.url
        
        # Извлекаем ID из URL
        url_parts = response.url.strip('/').split('/')
        item['id'] = url_parts[-1] if url_parts else None
        
        # Название
        if 'name' not in item or not item['name']:
            name_selector = self.config.get('name_selector', 'h1::text')
            item['name'] = response.css(name_selector).get('').strip()
        
        # Описание
        description = self.extract_description(response)
        if description:
            item['description'] = description
        
        # Особенности для классов
        if self.section == 'classes':
            features = self.extract_features(response)
            if features:
                item['features'] = features
        
        # Характеристики для заклинаний
        if self.section == 'spells':
            item['level'] = item.get('level')
            item['school'] = item.get('school')
            item['components'] = item.get('item_suffix')
            item['concentration'] = 'concentration' in item.get('item_tags', {})
            item['ritual'] = 'ritual' in item.get('item_tags', {})
        
        # Добавляем в детали
        self.details.append(item)
        self.stats['processed'] += 1
        self.processed_urls.add(response.url)
        
        # Показываем прогресс
        if index % 5 == 0 or index == 1 or index == self.stats['total_found']:
            print(f"  ✅ Обработано: {self.stats['processed']}/{self.stats['total_found']} - {item.get('name', 'Unknown')[:40]}")
        
        # Сохраняем каждые 10 элементов
        if len(self.details) % 10 == 0:
            self.save_progress()
        
        yield item
    
    def extract_description(self, response):
        """Извлекаем описание"""
        selectors = [
            self.config.get('description_selector', ''),
            'div.entry-content p::text',
            'div.description p::text',
            'div.content p::text',
            'article p::text',
            'main p::text',
            'div[class*="description"] p::text',
            'div[class*="content"] p::text',
        ]
        
        for selector in selectors:
            if selector:
                desc = response.css(selector).getall()
                if desc:
                    full_desc = ' '.join(desc).strip()
                    full_desc = re.sub(r'\s+', ' ', full_desc)
                    return full_desc
        
        return None
    
    def extract_features(self, response):
        """Извлекаем особенности классов"""
        features = []
        headings = response.css('h2, h3, h4')
        
        for heading in headings:
            heading_text = heading.css('::text').get()
            if heading_text and len(heading_text.strip()) > 3:
                next_p = heading.xpath('following-sibling::p[1]').css('::text').get()
                if next_p and len(next_p.strip()) > 10:
                    features.append({
                        'name': heading_text.strip(),
                        'description': next_p.strip()
                    })
        
        return features if features else None
    
    def handle_error(self, failure):
        """Обрабатываем ошибки"""
        error_info = {
            'url': failure.request.url,
            'error': str(failure.value),
            'time': datetime.now().isoformat()
        }
        self.errors.append(error_info)
        self.stats['failed'] += 1
        print(f"❌ Ошибка: {failure.request.url}")
        
        # Сохраняем ошибки
        self.save_json(self.files['errors'], self.errors)
    
    def save_json(self, filename, data):
        """Сохраняет данные в JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_stats(self):
        """Сохраняет статистику"""
        self.stats['last_update'] = datetime.now().isoformat()
        self.save_json(self.files['stats'], self.stats)
    
    def save_progress(self):
        """Сохраняет промежуточные результаты"""
        self.save_json(self.files['details'], self.details)
        self.save_stats()
        print(f"💾 Автосохранение: {len(self.details)} элементов")
    
    def save_summary(self):
        """Сохраняет сводку по разделу"""
        summary = {
            'section': self.config['name'],
            'total': len(self.details),
            'sources': self.stats['sources'],
            'files': self.files,
            'completion_date': datetime.now().isoformat()
        }
        self.save_json(self.files['summary'], summary)
    
    def closed(self, reason):
        """При закрытии паука"""
        self.stats['end_time'] = datetime.now().isoformat()
        self.stats['completion_reason'] = reason
        
        # Финальное сохранение
        self.save_progress()
        self.save_summary()
        
        print(f"\n{'='*60}")
        print(f"✅ ПАРСИНГ ЗАВЕРШЕН!")
        print(f"📊 Раздел: {self.config['name']}")
        print(f"📊 Найдено: {self.stats['total_found']}")
        print(f"📊 Обработано: {self.stats['processed']}")
        print(f"📊 Ошибок: {self.stats['failed']}")
        print(f"\n📁 Файлы сохранены в: {self.output_dir}")
        print(f"   - list.json - список всех элементов")
        print(f"   - details.json - детальная информация")
        print(f"   - stats.json - статистика")
        print(f"   - summary.json - сводка")
        if self.errors:
            print(f"   - errors.json - ошибки")
        print(f"{'='*60}\n")