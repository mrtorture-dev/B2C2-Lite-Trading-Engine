from django.core.management.base import BaseCommand
import requests
from django.core.cache import cache
from trading.models import Asset

class Command(BaseCommand):
    help = 'Sincroniza el Top 20 de criptos desde Binance automáticamente'

    def handle(self, *args, **kwargs):
        self.stdout.write("📡 Conectando con Binance API...")
        
        # Usamos el endpoint de ticker/24hr que nos da volumen y cambios
        url = "https://api.binance.com/api/v3/ticker/24hr"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            # 1. Filtrar solo pares con USDT (Ej: BTCUSDT, ETHUSDT)
            usdt_pairs = [item for item in data if item['symbol'].endswith('USDT')]
            
            # 2. Ordenar por VOLUMEN (quoteVolume) descendente
            sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            
            # 3. Tomar el Top 20
            top_20 = sorted_pairs[:20]
            
            prices_dict = {}
            count = 0
            for item in top_20:
                symbol = item['symbol']
                code = symbol.replace('USDT', '')
                
                if code in ['USDC', 'BUSD', 'DAI']: 
                    continue

                obj, created = Asset.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': code, 
                        'is_crypto': True
                    }
                )
                
                # Guardamos el precio en nuestro diccionario de cache
                prices_dict[code] = float(item['lastPrice'])
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✅ Nueva moneda: {code}'))
                else:
                    self.stdout.write(f'🔄 Actualizada/Verificada: {code}')

            # GUARDAR EN CACHE PARA EL DASHBOARD DE QUANT
            if prices_dict:
                cache.set('market_prices', prices_dict, timeout=60)
                self.stdout.write(self.style.SUCCESS(f'💾 Cache market_prices actualizado con {len(prices_dict)} activos.'))

            self.stdout.write(self.style.SUCCESS('✨ Sincronización completada.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))