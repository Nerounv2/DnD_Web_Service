import scrapy
import json
import re
import os
from datetime import datetime
from scrapy.http import Request

class UniversalDndSpider(scrapy.Spider):
    name = "universal_dnd"
    
    allowed_domains = ["dnd.su"]
    
    def __init__(self, section='all', limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.section = section
        self.limit = int(limit) if limit else None
        self.processed_count = 0
        
        # Конфигурация всех разделов
        self.sections = {
            'races': {
                'name': 'Расы',
                'type': 'html',
                'list_url': 'https://dnd.su/race/',
                'output_file': 'races.json',
                'list_selector': '.tile a.tile-wrapper.race',
                'fields': {
                    'name': '.article_title::text',
                    'name_en': '.article_title_en::text',
                }
            },
            'classes': {
                'name': 'Классы',
                'type': 'html',
                'list_url': 'https://dnd.su/class/',
                'output_file': 'classes.json',
                'list_selector': '.tile a.tile-wrapper.class',
                'fields': {
                    'name': '.article_title::text',
                    'name_en': '.article_title_en::text',
                }
            },
            'backgrounds': {
                'name': 'Предыстории',
                'type': 'html',
                'list_url': 'https://dnd.su/backgrounds/',
                'output_file': 'backgrounds.json',
                'list_selector': 'div.col.list-item__spell.for_filter a.list-item-wrapper',
            },
            'feats': {
                'name': 'Черты',
                'type': 'html',
                'list_url': 'https://dnd.su/feats/',
                'output_file': 'feats.json',
                'list_selector': 'div.col.list-item__spell.for_filter a.list-item-wrapper',
            },
            'spells': {
                'name': 'Заклинания',
                'type': 'api',
                'api_url': 'https://dnd.su/piece/spells/index-list/',
                'output_file': 'spells.json',
            },
            'items': {
                'name': 'Предметы',
                'type': 'api',
                'api_url': 'https://dnd.su/piece/items/index-list/',
                'output_file': 'items.json',
            }
        }
        
        # Результаты
        self.results = {key: [] for key in self.sections.keys()}
        
        print(f"\n{'='*60}")
        print(f"🚀 ЗАПУСК УНИВЕРСАЛЬНОГО ПАРСЕРА")
        print(f"📌 Раздел: {section}")
        if self.limit:
            print(f"📊 Лимит: {self.limit} записей на раздел")
        print(f"{'='*60}\n")
    
    def start_requests(self):
        if self.section == 'all':
            for name, config in self.sections.items():
                yield from self.create_request(name, config)
        else:
            config = self.sections.get(self.section)
            if config:
                yield from self.create_request(self.section, config)
    
    def create_request(self, section_name, config):
        """Создает запрос в зависимости от типа"""
        if config['type'] == 'api':
            yield Request(
                url=config['api_url'],
                callback=self.parse_api_list,
                meta={'section': section_name},
                dont_filter=True
            )
        else:
            yield Request(
                url=config['list_url'],
                callback=self.parse_html_list,
                meta={'section': section_name},
                dont_filter=True
            )
    
    def parse_html_list(self, response):
        """Парсим HTML страницу со списком"""
        section = response.meta['section']
        config = self.sections[section]
        
        print(f"\n📥 Парсим список {config['name']}...")
        
        items = response.css(config['list_selector'])
        print(f"✅ Найдено элементов: {len(items)}")
        
        if self.limit:
            items = items[:self.limit]
            print(f"🔍 Лимит {self.limit}: берем первые {len(items)}")
        
        for item in items:
            href = item.attrib.get('href', '')
            url = response.urljoin(href)
            
            # Для предысторий и черт - ищем родительский div с data-атрибутами
            parent = item.xpath('ancestor::div[contains(@class, "list-item__spell")]')
            
            yield Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    'section': section,
                    'url': url,
                    'name': item.css('::text').get('').strip(),
                    'data_id': parent.attrib.get('data-id', '') if parent else '',
                    'data_search': parent.attrib.get('data-search', '') if parent else ''
                },
                dont_filter=True
            )
    
    def parse_api_list(self, response):
        """Парсим API ответ"""
        section = response.meta['section']
        config = self.sections[section]
        
        print(f"\n📥 Парсим API {config['name']}...")
        
        match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
        
        if match:
            data = json.loads(match.group(1))
            items = data.get('cards', [])
            
            print(f"✅ Найдено элементов: {len(items)}")
            
            if self.limit:
                items = items[:self.limit]
                print(f"🔍 Лимит {self.limit}: берем первые {len(items)}")
            
            for item in items:
                if 'link' in item:
                    url = f"https://dnd.su{item['link']}"
                    
                    yield Request(
                        url=url,
                        callback=self.parse_detail,
                        meta={
                            'section': section,
                            'api_item': item
                        },
                        dont_filter=True
                    )
    
    def parse_detail(self, response):
        """Парсим детальную страницу"""
        section = response.meta['section']
        
        if section == 'races':
            result = self.parse_race(response, response.meta)
        elif section == 'classes':
            result = self.parse_class(response, response.meta)
        elif section == 'backgrounds':
            result = self.parse_background(response, response.meta)
        elif section == 'feats':
            result = self.parse_feat(response, response.meta)
        elif section == 'spells':
            result = self.parse_spell(response, response.meta)
        elif section == 'items':
            result = self.parse_item(response, response.meta)
        else:
            result = {'id': len(self.results.get(section, [])) + 1}
        
        self.results.setdefault(section, []).append(result)
        
        # Безопасный вывод названия
        # Безопасный вывод названия
        name_value = result.get('name', '')
        if name_value and isinstance(name_value, str):
            display_name = name_value[:30] + "..." if len(name_value) > 30 else name_value
            print(f"  ✅ {section}: {display_name}")
        else:
            print(f"  ✅ {section}: запись #{len(self.results[section])}")
        
        yield result
    
    def parse_race(self, response, meta):
        """Парсим расу"""
        result = {
            'id': len(self.results['races']) + 1,
            'name': meta.get('name', ''),
            'name_en': '',
            'description': '',
            'features': []
        }
        
        # Название
        name = response.css('h1.header-page_title a::text').get()
        if name:
            result['name'] = name.strip()
        
        # Английское название из meta
        if 'name_en' in meta:
            result['name_en'] = meta['name_en']
        
        # Описание
        desc_parts = []
        for p in response.css('div.entry-content p'):
            text = p.css('::text').get()
            if text and 'особенност' not in text.lower():
                desc_parts.append(text.strip())
            elif 'особенност' in text.lower():
                break
        result['description'] = ' '.join(desc_parts)
        
        # Особенности
        features = []
        features_header = response.xpath('//*[contains(text(), "Особенности")]')
        if features_header:
            for p in features_header[0].xpath('./following-sibling::p'):
                text = p.css('::text').get()
                if text and text.strip():
                    features.append(text.strip())
        
        if not features:
            keywords = ['Увеличение характеристик', 'Возраст', 'Размер', 'Скорость', 'Тёмное зрение']
            for p in response.css('div.entry-content p'):
                text = p.css('::text').get()
                if text and any(k in text for k in keywords):
                    features.append(text.strip())
        
        result['features'] = features
        return result
    
    def parse_class(self, response, meta):
        """Парсим класс (базовая версия)"""
        result = {
            'id': len(self.results['classes']) + 1,
            'name': meta.get('name', ''),
            'name_en': '',
            'description': '',
            'hits': {},
            'proficiencies': {},
            'equipment': [],
            'table': {'columns': [], 'rows': []},
            'features': []
        }
        return result
    
    def parse_background(self, response, meta):
        """Парсим предысторию"""
        result = {
            'id': len(self.results['backgrounds']) + 1,
            'name': meta.get('name', ''),
            'name_en': '',
            'description': '',
            'skills': [],
            'tools': [],
            'equipment': [],
            'feature': {},
            'personality_traits': [],
            'ideals': [],
            'bonds': [],
            'flaws': []
        }
        
        # Английское название из data-search
        if meta.get('data_search'):
            parts = meta['data_search'].split(',')
            if len(parts) >= 2:
                result['name_en'] = parts[1].strip().rstrip(',')
        
        # Описание
        desc = response.css('div.entry-content p::text').get()
        if desc:
            result['description'] = desc.strip()
        
        return result
    
    def parse_feat(self, response, meta):
        """Парсим черту"""
        result = {
            'id': len(self.results['feats']) + 1,
            'name': meta.get('name', ''),
            'name_en': '',
            'description': '',
            'prerequisite': 'Нет',
            'source': '',
            'benefits': []
        }
        
        if meta.get('data_search'):
            parts = meta['data_search'].split(',')
            if len(parts) >= 2:
                result['name_en'] = parts[1].strip().rstrip(',')
        
        return result
    
    def parse_spell(self, response, meta):
        """Парсим заклинание"""
        item = meta.get('api_item', {})
        result = {
            'id': len(self.results['spells']) + 1,
            'name': item.get('title', ''),
            'name_en': item.get('title_en', ''),
            'level': item.get('level', ''),
            'school': item.get('school', ''),
            'casting_time': '',
            'range': '',
            'components': {
                'verbal': False,
                'somatic': False,
                'material': False,
                'materials': ''
            },
            'duration': '',
            'classes': [],
            'source': '',
            'description': '',
            'higher_levels': ''
        }
        return result
    
    def parse_item(self, response, meta):
        """Парсим предмет"""
        item = meta.get('api_item', {})
        result = {
            'id': len(self.results['items']) + 1,
            'name': item.get('title', ''),
            'name_en': item.get('title_en', ''),
            'type': '',
            'rarity': '',
            'attunement': False,
            'source': '',
            'description': '',
            'properties': []
        }
        return result
    
    def closed(self, reason):
        """Сохраняем результаты"""
        for section, data in self.results.items():
            if data:
                filename = self.sections[section]['output_file']
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({section: data}, f, ensure_ascii=False, indent=2)
                print(f"✅ {filename} сохранен - {len(data)} записей")
        
        print(f"\n{'='*60}")
        print(f"✅ ПАРСИНГ ЗАВЕРШЕН!")
        print(f"{'='*60}\n")