import scrapy

class BackgroundsFinalSpider(scrapy.Spider):
    name = "backgrounds_final"
    
    allowed_domains = ["dnd.su"]
    start_urls = ['https://dnd.su/backgrounds/']
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"🔍 ПАРСИНГ ПРЕДЫСТОРИЙ")
        print(f"{'='*60}\n")
        
        # Находим ВСЕ предыстории
        items = response.css('div.col.list-item__spell.for_filter')
        print(f"✅ Найдено предысторий: {len(items)}")
        
        # Словарь для источников
        source_map = {
            '102': 'Player\'s Handbook',
            '115': 'Acquisition Incorporated',
            '117': 'Tasha\'s Cauldron of Everything',
            '109': 'Xanathar\'s Guide to Everything',
            '155': 'Strixhaven: A Curriculum of Chaos',
            '125': 'Van Richten\'s Guide to Ravenloft',
        }
        
        for i, item in enumerate(items, 1):
            # Данные из атрибутов
            data_id = item.attrib.get('data-id', '')
            data_source = item.attrib.get('data-source', '')
            data_search = item.attrib.get('data-search', '')
            
            # Извлекаем название и ссылку
            link = item.css('a.list-item-wrapper')
            if link:
                href = link.attrib.get('href', '')
                name = link.css('div.list-item-title::text').get()
                
                # Английское название из data-search
                name_en = ''
                if data_search and ',' in data_search:
                    parts = data_search.split(',')
                    if len(parts) >= 2:
                        name_en = parts[1].strip()
                
                # Источник
                source = source_map.get(data_source, f'Unknown ({data_source})')
                
                background = {
                    'id': data_id,
                    'name': name.strip() if name else '',
                    'name_en': name_en,
                    'source_code': data_source,
                    'source': source,
                    'url': response.urljoin(href) if href else '',
                }
                
                print(f"\n{i:3}. {background['name']}")
                print(f"    ID: {background['id']}")
                print(f"    English: {background['name_en']}")
                print(f"    Source: {background['source']}")
                print(f"    URL: {background['url']}")
                
                # Переходим на детальную страницу
                if href:
                    yield scrapy.Request(
                        url=response.urljoin(href),
                        callback=self.parse_detail,
                        meta={'background': background},
                        dont_filter=True
                    )
    
    def parse_detail(self, response):
        """Парсим детальную страницу"""
        background = response.meta['background']
        
        print(f"\n📖 {background['name']}")
        
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
        
        background['description'] = description[:5000] if description else ''
        background['detail_url'] = response.url
        
        print(f"   📝 Длина описания: {len(description)} символов")
        
        yield background