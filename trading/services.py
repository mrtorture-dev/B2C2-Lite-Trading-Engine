from django.db import transaction
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import Order, Wallet, Asset, Trade

class OrderService:
    
    @staticmethod
    def get_market_price(asset_code):
        """Obtiene el precio real de Binance desde Redis"""
        prices = cache.get('market_prices', {})
        return Decimal(str(prices.get(asset_code, 0)))

    @staticmethod
    def execute_lp_trade(user, asset_code, side, amount):
        """
        EJECUCIÓN INSTANTÁNEA CONTRA EL BOT (Con Spread del 1%)
        """
        market_price = OrderService.get_market_price(asset_code)
        if market_price == 0:
            raise ValueError("Mercado cerrado o sin precio.")

        # --- APLICAMOS LA LÓGICA DEL 1% DE SPREAD ---
        # Si el usuario COMPRA, el Bot le vende CARO (Price * 1.01)
        # Si el usuario VENDE, el Bot le compra BARATO (Price * 0.99)
        if side == 'BUY':
            final_price = market_price * Decimal("1.01")
        else:
            final_price = market_price * Decimal("0.99")

        amount = Decimal(str(amount))
        total_cost = amount * final_price

        # Usuario Sistema (Contraparte)
        User = get_user_model()
        system_user, _ = User.objects.get_or_create(username='B2C2_LIQUIDITY_PROVIDER')

        with transaction.atomic():
            asset = Asset.objects.get(code=asset_code)
            usd_asset = Asset.objects.get(code='USD')

            # 1. Crear Orden del Usuario (FILLED inmediatamente)
            user_order = Order.objects.create(
                user=user, asset=asset, side=side, 
                initial_amount=amount, price=final_price, status='FILLED'
            )

            # 2. Mover Fondos (Lógica estándar)
            if side == 'BUY':
                # Cobrar USD al usuario
                usd_wallet = Wallet.objects.select_for_update().get(user=user, asset=usd_asset)
                if usd_wallet.balance < total_cost:
                    raise ValueError(f"Saldo insuficiente. Necesitas {total_cost:.2f} USD (incluye 1% spread)")
                usd_wallet.balance -= total_cost
                usd_wallet.save()
                
                # Entregar Crypto
                crypto_wallet, _ = Wallet.objects.get_or_create(user=user, asset=asset)
                crypto_wallet.balance += amount
                crypto_wallet.save()

                # Crear contra-orden del sistema (SELL)
                system_order = Order.objects.create(
                    user=system_user, asset=asset, side='SELL',
                    initial_amount=amount, price=final_price, status='FILLED'
                )
                buyer, seller = user_order, system_order

            else: # SELL
                # Cobrar Crypto
                crypto_wallet = Wallet.objects.select_for_update().get(user=user, asset=asset)
                if crypto_wallet.balance < amount:
                    raise ValueError("No tienes suficientes monedas.")
                crypto_wallet.balance -= amount
                crypto_wallet.save()

                # Entregar USD
                usd_wallet, _ = Wallet.objects.get_or_create(user=user, asset=usd_asset)
                usd_wallet.balance += total_cost
                usd_wallet.save()

                # Crear contra-orden del sistema (BUY)
                system_order = Order.objects.create(
                    user=system_user, asset=asset, side='BUY',
                    initial_amount=amount, price=final_price, status='FILLED'
                )
                buyer, seller = system_order, user_order

            # 3. Registrar el Trade
            Trade.objects.create(
                buy_order=buyer, sell_order=seller,
                amount=amount, price=final_price
            )
            
            return user_order

    @staticmethod
    def create_p2p_limit_order(user, asset_code, side, amount, price):
        """
        CREA UNA ORDEN PENDIENTE (LIBRO DE ÓRDENES P2P)
        """
        with transaction.atomic():
            asset = Asset.objects.get(code=asset_code)
            # Validamos fondos antes de dejar poner la orden (Congelamos fondos teóricamente)
            # Por simplicidad en este tutorial, solo verificamos, no bloqueamos saldo aun.
            
            order = Order.objects.create(
                user=user,
                asset=asset,
                side=side,
                initial_amount=amount,
                price=price,
                status='PENDING' # <--- Queda esperando en el libro
            )
            return order

    @staticmethod
    def execute_p2p_match(taking_user, order_id):
        """
        OTRO USUARIO 'TOMADOR' ACEPTA UNA ORDEN 'PENDING'
        """
        with transaction.atomic():
            # La orden que estaba esperando (Maker)
            maker_order = Order.objects.select_for_update().get(id=order_id, status='PENDING')
            asset = maker_order.asset
            price = maker_order.price
            amount = maker_order.initial_amount
            total_cost = amount * price
            usd_asset = Asset.objects.get(code='USD')

            # Creamos la orden del que aceptó (Taker)
            taker_side = 'SELL' if maker_order.side == 'BUY' else 'BUY'
            
            taker_order = Order.objects.create(
                user=taking_user, asset=asset, side=taker_side,
                initial_amount=amount, price=price, status='FILLED'
            )

            # --- LÓGICA DE INTERCAMBIO DE FONDOS P2P ---
            # Identificamos quién es comprador y vendedor
            if maker_order.side == 'BUY':
                buyer = maker_order.user
                seller = taking_user
                buy_order_ref = maker_order
                sell_order_ref = taker_order
            else:
                buyer = taking_user
                seller = maker_order.user
                buy_order_ref = taker_order
                sell_order_ref = maker_order

            # 1. El Comprador paga USD
            buyer_usd = Wallet.objects.select_for_update().get(user=buyer, asset=usd_asset)
            if buyer_usd.balance < total_cost:
                raise ValueError(f"El comprador no tiene saldo suficiente ({total_cost})")
            buyer_usd.balance -= total_cost
            buyer_usd.save()

            # 2. El Vendedor recibe USD
            seller_usd, _ = Wallet.objects.get_or_create(user=seller, asset=usd_asset)
            seller_usd.balance += total_cost
            seller_usd.save()

            # 3. El Vendedor entrega Crypto
            seller_crypto = Wallet.objects.select_for_update().get(user=seller, asset=asset)
            if seller_crypto.balance < amount:
                raise ValueError("El vendedor no tiene suficientes criptos")
            seller_crypto.balance -= amount
            seller_crypto.save()

            # 4. El Comprador recibe Crypto
            buyer_crypto, _ = Wallet.objects.get_or_create(user=buyer, asset=asset)
            buyer_crypto.balance += amount
            buyer_crypto.save()

            # Actualizamos estado de la orden vieja
            maker_order.status = 'FILLED'
            maker_order.save()

            # Registramos el Trade
            Trade.objects.create(
                buy_order=buy_order_ref, sell_order=sell_order_ref,
                amount=amount, price=price
            )
    @staticmethod
    def cancel_order(user, order_id):
        """Cancela una orden propia si está pendiente"""
        try:
            order = Order.objects.get(id=order_id, user=user, status='PENDING')
            order.status = 'CANCELLED'
            order.save()
            return True
        except Order.DoesNotExist:
            raise ValueError("Order not found or not pending.")