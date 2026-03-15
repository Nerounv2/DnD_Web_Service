import scrapy
import json
import re
from scrapy.http import Request

class UniversalDndSpider(scrapy.Spider):
    name = "universal_dnd"
    
    allowed_domains = ["dnd.su"]
    
    # Конфигурация для разделов
    SECTIONS = {
        'spells': {
            'name': 'Заклинания',
            'list_url': 'https://dnd.su/spells/',
            'list_type': 'api',
            'data_endpoint': '/piece/spells/index-list/',
            'item_pattern': r'/spells/[\w-]+/',
            'item_selector': '.cards_list__item a',
            'name_selector': 'h1.header-page_title a::text, h1::text',
            'description_selector': 'div.entry-content p::text',
            'output_file': 'spells_all.json'
        },
        'classes': {
            'name': 'Классы',
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
            'output_file': 'classes_all.json'
        }
    }
    
    def __init__(self, section='spells', *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if section not in self.SECTIONS:
            raise ValueError(f"Раздел должен быть одним из: {list(self.SECTIONS.keys())}")
        
        self.section = section
        self.config = self.SECTIONS[section]
        
        # Для сбора результатов
        self.results = []
        self.processed_urls = set()
        self.total_items = 0
        
        print(f"\n{'='*60}")
        print(f"🚀 ЗАПУСК ПАРСИНГА: {self.config['name']}")
        print(f"📁 Режим: {self.config['list_type']}")
        print(f"📄 Выходной файл: {self.config['output_file']}")
        print(f"{'='*60}\n")
    
    def start_requests(self):
        """Начинаем с получения списка"""
        if self.config['list_type'] == 'api':
            # Для заклинаний - через API
            endpoint = f"https://dnd.su{self.config['data_endpoint']}"
            yield Request(
                url=endpoint,
                callback=self.parse_api_list,
                errback=self.handle_error,
                dont_filter=True
            )
        else:
            # Для классов - через HTML
            yield Request(
                url=self.config['list_url'],
                callback=self.parse_html_list,
                errback=self.handle_error,
                dont_filter=True
            )
    
    def parse_api_list(self, response):
        """Парсим список из API (для заклинаний)"""
        print(f"\n📥 Получаем список {self.config['name']} через API...")
        
        # Ищем window.LIST
        match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            data = json.loads(json_str)
            items = data.get('cards', [])
            
            self.total_items = len(items)
            print(f"✅ Найдено {self.total_items} {self.config['name']}")
            
            # Сохраняем список
            list_file = f"{self.section}_list.json"
            with open(list_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"💾 Список сохранен в {list_file}")
            
            # Создаем запросы для каждого элемента
            for i, item in enumerate(items, 1):
                if 'link' in item:
                    url = f"https://dnd.su{item['link']}"
                    
                    # Показываем прогресс
                    if i % 50 == 0 or i == 1:
                        print(f"  ⏳ Добавлено в очередь: {i}/{self.total_items}")
                    
                    yield Request(
                        url=url,
                        callback=self.parse_detail,
                        errback=self.handle_error,
                        meta={'item': item, 'index': i},
                        dont_filter=True
                    )
            
            print(f"\n✅ Все {self.total_items} {self.config['name']} добавлены в очередь!")
        else:
            print("❌ API не сработал, пробуем HTML...")
            yield Request(
                url=self.config['list_url'],
                callback=self.parse_html_list,
                errback=self.handle_error,
                dont_filter=True
            )
    
    def parse_html_list(self, response):
        """Парсим список из HTML (для классов)"""
        print(f"\n📥 Парсим HTML список {self.config['name']}...")
        
        items = []
        
        # Используем селектор из конфига
        selector = self.config.get('item_selector')
        if selector:
            elements = response.css(selector)
            print(f"Найдено элементов по селектору: {len(elements)}")
            
            for elem in elements:
                item = {
                    'url': response.urljoin(elem.attrib.get('href', '')),
                }
                
                # Извлекаем поля
                fields = self.config.get('fields', {})
                for field_name, field_selector in fields.items():
                    value = elem.css(field_selector).get()
                    if value:
                        item[field_name] = value.strip()
                
                # Извлекаем иконку
                if 'icon' in item:
                    icon_match = re.search(r'sprite-class__(\w+)', item['icon'])
                    if icon_match:
                        item['icon_name'] = icon_match.group(1)
                
                items.append(item)
            
            self.total_items = len(items)
            print(f"✅ Найдено {self.total_items} {self.config['name']}")
            
            # Сохраняем список
            list_file = f"{self.section}_list.json"
            with open(list_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"💾 Список сохранен в {list_file}")
            
            # Создаем запросы для каждого элемента
            for i, item in enumerate(items, 1):
                # Показываем прогресс
                if i % 5 == 0 or i == 1 or i == self.total_items:
                    print(f"  ⏳ Добавлено в очередь: {i}/{self.total_items}")
                
                yield Request(
                    url=item['url'],
                    callback=self.parse_detail,
                    errback=self.handle_error,
                    meta={'item': item, 'index': i},
                    dont_filter=True
                )
            
            print(f"\n✅ Все {self.total_items} {self.config['name']} добавлены в очередь!")
    
    def parse_detail(self, response):
        """Парсим детальную страницу"""
        item = response.meta['item'].copy()
        index = response.meta.get('index', 0)
        
        # Добавляем URL
        item['url'] = response.url
        
        # Название (если не было)
        if 'name' not in item or not item['name']:
            name_selector = self.config.get('name_selector', 'h1::text')
            item['name'] = response.css(name_selector).get('').strip()
        
        # Описание
        description = self.extract_description(response)
        if description:
            item['description'] = description
        
        # Особенности (для классов)
        if self.section == 'classes':
            features = self.extract_features(response)
            if features:
                item['features'] = features
        
        # Добавляем в результаты
        self.results.append(item)
        self.processed_urls.add(response.url)
        
        # Показываем прогресс
        if index % 5 == 0 or index == 1 or index == self.total_items:
            print(f"  ✅ Обработано: {len(self.results)}/{self.total_items} - {item.get('name', 'Unknown')[:30]}...")
        
        # Периодически сохраняем
        if len(self.results) % 10 == 0:
            self.save_results()
        
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
        ]
        
        for selector in selectors:
            if selector:
                desc = response.css(selector).getall()
                if desc:
                    # Объединяем и чистим
                    full_desc = ' '.join(desc).strip()
                    # Убираем множественные пробелы
                    full_desc = re.sub(r'\s+', ' ', full_desc)
                    return full_desc
        
        return None
    
    def extract_features(self, response):
        """Извлекаем особенности классов"""
        features = []
        
        # Ищем заголовки и следующий за ними текст
        headings = response.css('h2, h3, h4')
        for heading in headings:
            heading_text = heading.css('::text').get()
            if heading_text and len(heading_text.strip()) > 3:
                # Ищем следующий параграф
                next_p = heading.xpath('following-sibling::p[1]').css('::text').get()
                if next_p and len(next_p.strip()) > 10:
                    features.append({
                        'name': heading_text.strip(),
                        'description': next_p.strip()
                    })
        
        return features if features else None
    
    def handle_error(self, failure):
        """Обрабатываем ошибки"""
        print(f"❌ Ошибка при загрузке: {failure.request.url}")
        print(f"   Причина: {failure.value}")
    
    def save_results(self):
        """Сохраняем результаты"""
        output_file = self.config['output_file']
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"💾 Автосохранение: {len(self.results)} элементов в {output_file}")
    
    def closed(self, reason):
        """При закрытии паука"""
        self.save_results()
        print(f"\n{'='*60}")
        print(f"✅ ПАРСИНГ ЗАВЕРШЕН!")
        print(f"📊 Раздел: {self.config['name']}")
        print(f"📊 Всего обработано: {len(self.results)} из {self.total_items}")
        print(f"📁 Результаты сохранены в: {self.config['output_file']}")
        print(f"{'='*60}\n")