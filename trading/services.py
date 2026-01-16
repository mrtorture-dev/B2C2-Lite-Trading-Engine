from django.db import transaction
from decimal import Decimal
from .models import Order, Wallet, Asset

class OrderService:
    
    @staticmethod
    def create_order(user, asset_code, side, amount, price):
        """
        Crea una orden de manera segura usando transacciones atómicas de base de datos.
        Esto previene condiciones de carrera (race conditions).
        """
        amount = Decimal(str(amount))
        price = Decimal(str(price))
        total_cost = amount * price

        # INICIO DE LA TRANSACCIÓN (ACID)
        # Si algo falla aquí dentro, nada se guarda en la base de datos.
        with transaction.atomic():
            asset = Asset.objects.get(code=asset_code)
            
            # Lógica para COMPRA (BUY)
            if side == 'BUY':
                # Buscamos la wallet de USD del usuario para cobrarle
                # select_for_update() BLOQUEA la fila en la BD hasta terminar la transacción
                # Esto evita que el usuario gaste el mismo dinero dos veces en milisegundos.
                usd_asset = Asset.objects.get(code='USD')
                wallet = Wallet.objects.select_for_update().get(user=user, asset=usd_asset)
                
                if wallet.balance < total_cost:
                    raise ValueError(f"Saldo insuficiente. Tienes {wallet.balance}, necesitas {total_cost}")
                
                # Restamos saldo y lo pasamos a 'bloqueado' (opcional, aquí solo restamos por simplicidad)
                wallet.balance -= total_cost
                wallet.save()

            # Lógica para VENTA (SELL)
            elif side == 'SELL':
                wallet = Wallet.objects.select_for_update().get(user=user, asset=asset)
                
                if wallet.balance < amount:
                    raise ValueError(f"Saldo insuficiente. Tienes {wallet.balance} {asset.code}")

                wallet.balance -= amount
                wallet.save()

            # Finalmente, creamos la orden en la BD
            order = Order.objects.create(
                user=user,
                asset=asset,
                side=side,
                initial_amount=amount,
                price=price,
                status='PENDING' # O 'FILLED' si fuera mercado, simplificado aquí
            )
            
            return order