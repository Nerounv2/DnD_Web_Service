import scrapy
import json
import re
from scrapy.http import Request

class FeatsSpider(scrapy.Spider):
    name = "feats"
    
    allowed_domains = ["dnd.su"]
    start_urls = ['https://dnd.su/feats/']
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"🔍 НАЧИНАЕМ ПАРСИНГ ЧЕРТ")
        print(f"{'='*60}\n")
        
        # Находим все черты на странице
        feats = response.css('div.col.list-item__spell.for_filter')
        print(f"✅ Найдено черт на странице: {len(feats)}")
        
        if len(feats) == 0:
            print("❌ Черты не найдены! Проверяем структуру...")
            # Попробуем другой селектор
            feats = response.css('.list-item__spell')
            print(f"   По классу .list-item__spell: {len(feats)}")
            
            if len(feats) > 0:
                print("✅ Нашли через .list-item__spell!")
        
        # Словарь для соответствия кодов источников
        source_map = {
            '102': 'Player\'s Handbook',
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
        
        # Собираем все черты
        feats_list = []
        
        for i, feat in enumerate(feats, 1):
            # Извлекаем данные из атрибутов
            data_id = feat.attrib.get('data-id', '')
            data_source = feat.attrib.get('data-source', '')
            data_search = feat.attrib.get('data-search', '')
            data_letter = feat.attrib.get('data-letter', '')
            
            # Название и ссылка
            link_elem = feat.css('a.list-item-wrapper')
            if link_elem:
                href = link_elem.attrib.get('href', '')
                name = link_elem.css('div.list-item-title::text').get()
            else:
                href = ''
                name = ''
            
            # Извлекаем английское название из data-search
            name_en = ''
            if data_search and ',' in data_search:
                parts = data_search.split(',')
                if len(parts) >= 2:
                    name_en = parts[1].strip().rstrip(',')
            
            # Определяем источник
            source = source_map.get(data_source, f'Unknown ({data_source})')
            
            # Создаем запись
            feat_item = {
                'id': data_id,
                'name': name.strip() if name else '',
                'name_en': name_en,
                'source_code': data_source,
                'source': source,
                'url': response.urljoin(href) if href else '',
                'letter': data_letter,
                'search_data': data_search,
            }
            
            feats_list.append(feat_item)
            
            print(f"\n{i:2}. {feat_item['name']}")
            print(f"    ID: {feat_item['id']}")
            print(f"    English: {feat_item['name_en']}")
            print(f"    Источник: {feat_item['source']}")
            print(f"    Ссылка: {feat_item['url']}")
            
            # Переходим на страницу черты за подробностями
            if href:
                yield Request(
                    url=response.urljoin(href),
                    callback=self.parse_feat_detail,
                    meta={'feat': feat_item},
                    dont_filter=True
                )
        
        # Сохраняем список всех черт
        with open('feats_list.json', 'w', encoding='utf-8') as f:
            json.dump(feats_list, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✅ ВСЕГО НАЙДЕНО ЧЕРТ: {len(feats_list)}")
        print(f"📁 Список сохранен в feats_list.json")
        print(f"{'='*60}")
    
    def parse_feat_detail(self, response):
        """Парсим детальную страницу черты"""
        feat = response.meta['feat']
        
        print(f"\n📖 Детально: {feat['name']}")
        print(f"   URL: {response.url}")
        
        # Ищем описание разными способами
        description = ''
        
        # Способ 1: Основной контент
        content = response.css('div.entry-content')
        if content:
            paragraphs = content.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        # Способ 2: Все параграфы
        if not description:
            paragraphs = response.css('p::text').getall()
            if paragraphs:
                description = ' '.join(paragraphs).strip()
        
        # Способ 3: Весь текст страницы (очищенный)
        if not description:
            all_text = response.css('body *::text').getall()
            # Фильтруем короткие строки
            clean_text = [t.strip() for t in all_text if len(t.strip()) > 30]
            description = ' '.join(clean_text)
        
        # Ищем требования
        requirements = ''
        req_patterns = [
            '//p[contains(text(), "Требование")]/following-sibling::p[1]/text()',
            '//p[contains(text(), "Prerequisite")]/following-sibling::p[1]/text()',
            '//p[contains(text(), "требуется")]/following-sibling::p[1]/text()',
        ]
        
        for pattern in req_patterns:
            req = response.xpath(pattern).get()
            if req:
                requirements = req.strip()
                break
        
        # Ищем эффекты
        effects = []
        effect_patterns = [
            '//h2[contains(text(), "Эффект")]/following-sibling::p/text()',
            '//h3[contains(text(), "Эффект")]/following-sibling::p/text()',
            '//h2[contains(text(), "Effect")]/following-sibling::p/text()',
        ]
        
        for pattern in effect_patterns:
            effect = response.xpath(pattern).get()
            if effect:
                effects.append(effect.strip())
        
        # Добавляем информацию
        feat['description'] = description[:5000] if description else ''  # Ограничим длину
        feat['requirements'] = requirements
        feat['effects'] = effects if effects else None
        feat['url'] = response.url
        
        print(f"   📝 Длина описания: {len(description)} символов")
        if requirements:
            print(f"   ⚡ Требования: {requirements[:100]}...")
        if effects:
            print(f"   ✨ Найдено эффектов: {len(effects)}")
        
        yield feat
    
    def closed(self, reason):
        print(f"\n{'='*60}")
        print(f"✅ ПАРСИНГ ЧЕРТ ЗАВЕРШЕН!")
        print(f"📊 Причина: {reason}")
        print(f"{'='*60}\n")