import scrapy
import json

class TestClassesSpider(scrapy.Spider):
    name = "test_classes"
    
    allowed_domains = ["dnd.su"]
    start_urls = ['https://dnd.su/class/']
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"🔍 Тестируем парсинг классов")
        print(f"URL: {response.url}")
        print(f"{'='*60}\n")
        
        # Ищем все плитки классов
        tiles = response.css('.tile a.tile-wrapper.class')
        print(f"Найдено плиток классов: {len(tiles)}")
        
        # Покажем первые 3 для проверки
        for i, tile in enumerate(tiles[:3]):
            print(f"\n--- Класс {i+1} ---")
            
            # Извлекаем данные
            name = tile.css('.article_title::text').get()
            name_en = tile.css('.article_title_en::text').get()
            source = tile.css('.article_source::text').get()
            href = tile.attrib.get('href', '')
            
            # Иконка (извлекаем класс иконки)
            icon_class = tile.css('.tile__icon::attr(class)').get()
            icon_name = None
            if icon_class:
                # Ищем что-то типа sprite-class__bard
                import re
                match = re.search(r'sprite-class__(\w+)', icon_class)
                if match:
                    icon_name = match.group(1)
            
            print(f"  Название: {name}")
            print(f"  Английское: {name_en}")
            print(f"  Источник: {source}")
            print(f"  Ссылка: {href}")
            print(f"  Иконка: {icon_name}")
            
            # Сразу создаем item
            item = {
                'name': name,
                'name_en': name_en,
                'source': source,
                'url': response.urljoin(href),
                'icon': icon_name,
            }
            
            # Здесь же можем перейти на детальную страницу
            yield scrapy.Request(
                url=response.urljoin(href),
                callback=self.parse_class_detail,
                meta={'class_info': item}
            )
    
    def parse_class_detail(self, response):
        """Парсим детальную страницу класса"""
        class_info = response.meta['class_info']
        
        print(f"\n📖 Детальная страница: {class_info['name']}")
        print(f"URL: {response.url}")
        
        # Ищем описание
        description_parts = []
        
        # Пробуем разные селекторы для описания
        selectors = [
            'div.entry-content p::text',
            'div.class-description p::text',
            'div.content p::text',
            'article p::text',
        ]
        
        for selector in selectors:
            parts = response.css(selector).getall()
            if parts:
                description_parts = parts
                print(f"  ✅ Нашли описание через: {selector}")
                break
        
        if description_parts:
            class_info['description'] = ' '.join(description_parts).strip()
            print(f"  📝 Длина описания: {len(class_info['description'])} символов")
            print(f"  📝 Первые 100 символов: {class_info['description'][:100]}...")
        else:
            print(f"  ❌ Описание не найдено")
        
        # Ищем особенности класса
        features = []
        
        # Ищем блоки с особенностями (обычно h2 или h3 с последующим текстом)
        feature_headings = response.css('h2, h3')
        for heading in feature_headings:
            heading_text = heading.css('::text').get()
            if heading_text and len(heading_text.strip()) > 3:
                # Ищем следующий параграф
                next_p = heading.xpath('following-sibling::p[1]').css('::text').get()
                if next_p:
                    features.append({
                        'name': heading_text.strip(),
                        'description': next_p.strip()
                    })
        
        if features:
            class_info['features'] = features
            print(f"  ✨ Найдено особенностей: {len(features)}")
        
        # Возвращаем готовый item
        yield class_info

    def closed(self, reason):
        print(f"\n{'='*60}")
        print(f"✅ Тестирование завершено!")
        print(f"📊 Причина: {reason}")
        print(f"{'='*60}")