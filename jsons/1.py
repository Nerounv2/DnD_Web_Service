import requests
import requests


r=requests.get('https://dnd.su/spells/', timeout=10)
print(f'Статус: {r.status_code}, Размер: {len(r.text)}')