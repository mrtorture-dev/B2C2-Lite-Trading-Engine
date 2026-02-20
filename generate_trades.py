import os
import django
import random
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from trading.models import Asset, Order, Trade
from django.contrib.auth.models import User
from django.core.cache import cache

def generate():
    user = User.objects.get(username='whitealfa')
    btc, _ = Asset.objects.get_or_create(code='BTC', defaults={'name': 'Bitcoin', 'is_crypto': True})
    
    # FETCH REAL PRICE FROM CACHE
    prices = cache.get('market_prices', {})
    base_price = float(prices.get('BTC', 95000.0)) # Fallback to 95k if cache empty
    
    print(f"🚀 Generating 5 HFT Trades using Market Reference: ${base_price}...")
    
    for i in range(5):
        price = Decimal(f"{base_price + random.uniform(-1000, 1000):.2f}")
        amount = Decimal(f"{random.uniform(0.01, 0.1):.4f}")
        
        # Create Orders first
        b_order = Order.objects.create(user=user, asset=btc, side='BUY', initial_amount=amount, price=price, status='FILLED')
        s_order = Order.objects.create(user=user, asset=btc, side='SELL', initial_amount=amount, price=price, status='FILLED')
        
        # Create Trade
        Trade.objects.create(buy_order=b_order, sell_order=s_order, amount=amount, price=price)
        print(f"   - Created Trade {i+1}: {amount} BTC @ ${price}")

if __name__ == "__main__":
    generate()
