import scrapy
import json
import re

class DndSuSpider(scrapy.Spider):
    name = "dnd_su"
    
    allowed_domains = ["dnd.su"]
    start_urls = ['https://dnd.su/spells/']  # Просто начинаем с этой страницы
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"Парсим страницу: {response.url}")
        print(f"Статус ответа: {response.status}")
        print(f"Размер ответа: {len(response.text)} байт")
        
        # Проверяем, загрузилась ли страница
        if response.status != 200:
            print(f"❌ Ошибка загрузки: {response.status}")
            return
        
        # Ищем window.LIST
        if 'window.LIST' not in response.text:
            print("❌ window.LIST не найден на странице!")
            # Сохраним страницу для анализа
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("✅ Страница сохранена в debug_page.html для анализа")
            return
        
        print("✅ window.LIST найден!")
        
        # Ищем скрипты
        scripts = response.css('script::text').getall()
        print(f"Найдено скриптов: {len(scripts)}")
        
        for i, script in enumerate(scripts):
            if 'window.LIST' in script:
                print(f"✅ Скрипт #{i} содержит window.LIST")
                
                # Простое извлечение - берем всё содержимое скрипта
                try:
                    # Находим начало JSON
                    start = script.find('window.LIST = ') + len('window.LIST = ')
                    if start == -1:
                        start = script.find('window.LIST=') + len('window.LIST=')
                    
                    if start > 0:
                        # Ищем конец JSON (точку с запятой или конец строки)
                        end = script.find(';', start)
                        if end == -1:
                            end = len(script)
                        
                        json_str = script[start:end].strip()
                        print(f"Длина JSON: {len(json_str)} символов")
                        
                        # Пробуем распарсить
                        data = json.loads(json_str)
                        spells = data.get('cards', [])
                        
                        print(f"✅ Найдено заклинаний: {len(spells)}")
                        
                        # Сохраняем статистику
                        levels = {}
                        schools = {}
                        
                        for spell in spells:
                            level = spell.get('level', 'unknown')
                            school = spell.get('school', 'unknown')
                            levels[level] = levels.get(level, 0) + 1
                            schools[school] = schools.get(school, 0) + 1
                            
                            # Создаем item
                            yield {
                                'name': spell.get('title'),
                                'name_en': spell.get('title_en'),
                                'level': level,
                                'school': school,
                                'url': response.urljoin(spell.get('link', '')),
                                'components': spell.get('item_suffix', ''),
                                'has_concentration': 'concentration' in spell.get('item_tags', {}),
                                'has_ritual': 'ritual' in spell.get('item_tags', {}),
                            }
                        
                        # Выводим статистику
                        print(f"\n📊 Статистика по уровням:")
                        for level, count in sorted(levels.items()):
                            print(f"  Уровень {level}: {count}")
                        
                        print(f"\n🏫 Статистика по школам:")
                        for school, count in sorted(schools.items()):
                            print(f"  {school}: {count}")
                        
                        # Выходим после успешной обработки
                        return
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка парсинга JSON: {e}")
                    # Сохраняем для отладки
                    with open('debug_json_error.txt', 'w', encoding='utf-8') as f:
                        f.write(json_str[:1000])
                except Exception as e:
                    print(f"❌ Неожиданная ошибка: {e}")
        
        print("❌ Не удалось найти window.LIST в скриптах")