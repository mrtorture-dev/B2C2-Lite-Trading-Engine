from django.core.management.base import BaseCommand
import requests
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
            # Esto nos asegura tener las monedas importantes, no las "shitcoins"
            sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            
            # 3. Tomar el Top 20
            top_20 = sorted_pairs[:20]
            
            count = 0
            for item in top_20:
                symbol = item['symbol']
                # Quitamos 'USDT' del nombre (BTCUSDT -> BTC)
                code = symbol.replace('USDT', '')
                
                # Evitamos monedas raras o stablecoins que no queramos (opcional)
                if code in ['USDC', 'BUSD', 'DAI']: 
                    continue

                # update_or_create es más potente que get_or_create
                # Busca por 'code'. Si existe, actualiza 'defaults'. Si no, crea.
                obj, created = Asset.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': code, 
                        'is_crypto': True
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✅ Nueva moneda: {code}'))
                else:
                    # Si ya existe, no tocamos nada crítico, solo aseguramos que is_crypto sea True
                    self.stdout.write(f'🔄 Actualizada/Verificada: {code}')

            self.stdout.write(self.style.SUCCESS(f'✨ Sincronización completada. {count} nuevas monedas agregadas.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))