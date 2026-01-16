from celery import shared_task
import requests
from django.core.cache import cache
from .models import Asset

@shared_task
def fetch_binance_prices():
    """
    Busca precios en Binance para todos los criptoactivos activos en nuestra BD.
    """
    # 1. Obtenemos qué monedas tenemos registradas (BTC, ETH, SOL...)
    # Excluimos USD porque es la moneda base.
    crypto_assets = Asset.objects.filter(is_crypto=True).values_list('code', flat=True)
    
    if not crypto_assets:
        return
        
    base_url = "https://api.binance.com/api/v3/ticker/price"
    prices_dict = {}

    try:
        # Binance espera símbolos como 'BTCUSDT', 'ETHUSDT'
        # Haremos una petición por cada moneda (o podríamos pedir todas, pero filtramos)
        for code in crypto_assets:
            symbol = f"{code}USDT" # Asumimos paridad con Tether/Dólar
            response = requests.get(f"{base_url}?symbol={symbol}", timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                # Guardamos: 'BTC': 95000.00
                prices_dict[code] = float(data['price'])
            else:
                print(f"⚠️ Binance error for {symbol}: {response.status_code}")

        # Guardamos TODO el diccionario de precios en Redis
        # Clave: 'market_prices' (antes usábamos 'btc_price')
        if prices_dict:
            cache.set('market_prices', prices_dict, timeout=60)
            print(f"✅ Precios Binance actualizados: {prices_dict.keys()}")
            
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
