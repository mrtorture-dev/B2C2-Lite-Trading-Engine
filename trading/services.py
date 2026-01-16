from django.db import transaction
from decimal import Decimal
from .models import Order, Wallet, Asset

class OrderService:
    
    @staticmethod
    def create_order(user, asset_code, side, amount, price):
        amount = Decimal(str(amount))
        price = Decimal(str(price))
        total_cost = amount * price

        with transaction.atomic():
            asset = Asset.objects.get(code=asset_code)
            
            # --- LÓGICA DE COMPRA (BUY) ---
            if side == 'BUY':
                # 1. Cobrar USD
                usd_asset = Asset.objects.get(code='USD')
                # Bloqueamos la wallet de USD para evitar doble gasto
                usd_wallet = Wallet.objects.select_for_update().get(user=user, asset=usd_asset)
                
                if usd_wallet.balance < total_cost:
                    raise ValueError(f"Saldo insuficiente. Tienes {usd_wallet.balance}, necesitas {total_cost}")
                
                usd_wallet.balance -= total_cost
                usd_wallet.save()

                # 2. Entregar el Activo (BTC) - ¡AQUÍ ESTABA EL BUG!
                # get_or_create: Si existe la trae, si no existe la crea con balance 0
                target_wallet, created = Wallet.objects.get_or_create(
                    user=user, 
                    asset=asset,
                    defaults={'balance': 0}
                )
                
                # Si ya existía, la bloqueamos por seguridad; si es nueva, ya es nuestra
                if not created:
                    target_wallet = Wallet.objects.select_for_update().get(pk=target_wallet.pk)

                target_wallet.balance += amount
                target_wallet.save()

            # --- LÓGICA DE VENTA (SELL) ---
            elif side == 'SELL':
                # 1. Cobrar el Activo (BTC)
                # Aquí asumimos que la wallet DEBE existir si va a vender
                try:
                    wallet = Wallet.objects.select_for_update().get(user=user, asset=asset)
                except Wallet.DoesNotExist:
                    raise ValueError(f"No tienes una billetera de {asset.code}")

                if wallet.balance < amount:
                    raise ValueError(f"Saldo insuficiente. Tienes {wallet.balance} {asset.code}")

                wallet.balance -= amount
                wallet.save()

                # 2. Entregar USD
                usd_asset = Asset.objects.get(code='USD')
                usd_wallet, created = Wallet.objects.get_or_create(
                    user=user, 
                    asset=usd_asset, 
                    defaults={'balance': 0}
                )
                
                if not created:
                    usd_wallet = Wallet.objects.select_for_update().get(pk=usd_wallet.pk)
                    
                usd_wallet.balance += total_cost
                usd_wallet.save()

            # Registrar la Orden
            order = Order.objects.create(
                user=user,
                asset=asset,
                side=side,
                initial_amount=amount,
                price=price,
                status='FILLED' # Ya se ejecutó
            )
            
            return order
