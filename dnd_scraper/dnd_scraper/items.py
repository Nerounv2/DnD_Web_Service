# items.py
import scrapy

class DndItem(scrapy.Item):
    # определите поля для вашего элемента
    url = scrapy.Field()
    name = scrapy.Field()
    description = scrapy.Field()
    content = scrapy.Field()
    # Добавьте специфические поля для разных типов страниц
    spell_school = scrapy.Field()
    spell_level = scrapy.Field()
    monster_size = scrapy.Field()
    monster_type = scrapy.Field()
    # ... и так далее