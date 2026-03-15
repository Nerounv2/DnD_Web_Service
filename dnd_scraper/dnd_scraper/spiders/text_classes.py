import scrapy
import json
import re

class TestItemsSpider(scrapy.Spider):
    name = "test_items"
    
    def start_requests(self):
        url = 'https://dnd.su/piece/items/index-list/'
        print(f"\n{'='*60}")
        print(f"🔍 ТЕСТИРУЕМ API ПРЕДМЕТОВ")
        print(f"URL: {url}")
        print(f"{'='*60}\n")
        
        yield scrapy.Request(
            url=url,
            callback=self.parse,
            errback=self.handle_error,
            dont_filter=True
        )
    
    def parse(self, response):
        print(f"Статус: {response.status}")
        print(f"Размер ответа: {len(response.text)} байт")
        print(f"Content-Type: {response.headers.get('Content-Type', b'').decode()}")
        
        # Сохраняем для анализа
        with open('items_api_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("✅ Ответ сохранен в items_api_response.html")
        
        # Ищем window.LIST
        if 'window.LIST' in response.text:
            print("✅ window.LIST найден!")
            
            # Найдем его позицию
            pos = response.text.find('window.LIST')
            print(f"Позиция: {pos}")
            
            # Покажем контекст
            start = max(0, pos - 50)
            end = min(len(response.text), pos + 200)
            print("\nКонтекст вокруг window.LIST:")
            print(response.text[start:end])
            
            # Пробуем извлечь JSON
            match = re.search(r'window\.LIST\s*=\s*(\{.*?\});', response.text, re.DOTALL)
            if match:
                json_str = match.group(1)
                print(f"\nДлина JSON: {len(json_str)} символов")
                
                try:
                    data = json.loads(json_str)
                    print("✅ JSON успешно распарсен!")
                    print(f"Ключи в данных: {list(data.keys())}")
                    
                    cards = data.get('cards', [])
                    print(f"Найдено cards: {len(cards)}")
                    
                    if len(cards) > 0:
                        print("\nПервый предмет:")
                        first = cards[0]
                        for key, value in first.items():
                            print(f"  {key}: {value}")
                    else:
                        print("❌ cards пустой!")
                        
                        # Посмотрим, что есть в data
                        print("\nВсе ключи data:")
                        for key in data.keys():
                            print(f"  {key}")
                            
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка парсинга JSON: {e}")
                    # Сохраним проблемный JSON
                    with open('items_json_error.txt', 'w', encoding='utf-8') as f:
                        f.write(json_str[:1000])
            else:
                print("❌ Не удалось извлечь JSON")
        else:
            print("❌ window.LIST не найден!")
            print("\nПервые 500 символов ответа:")
            print(response.text[:500])
    
    def handle_error(self, failure):
        print(f"\n❌ Ошибка: {failure.value}")