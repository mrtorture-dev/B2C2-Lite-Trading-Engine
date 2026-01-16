from celery import shared_task
import requests
from django.core.cache import cache

@shared_task
def fetch_btc_price():
    """Consulta CoinGecko y guarda el precio en Cache (Redis) por 60 segundos"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        price = data['bitcoin']['usd']
        
        # Guardamos en Redis con la clave 'btc_price'
        cache.set('btc_price', price, timeout=60)
        
        print(f"✅ Precio actualizado: ${price}")
        return price
    except Exception as e:
        print(f"❌ Error obteniendo precio: {e}")