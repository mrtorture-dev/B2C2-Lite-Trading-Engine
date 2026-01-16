import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from trading.models import Asset, Wallet
from trading.services import OrderService  # <--- Importamos tu nueva lógica

User = get_user_model()

@pytest.mark.django_db
class TestTradingLogic:
    
    def setup_method(self):
        # Configuración inicial
        self.user = User.objects.create_user(username='trader', password='password123')
        self.usd = Asset.objects.create(code='USD', name='Dollar', is_crypto=False)
        self.btc = Asset.objects.create(code='BTC', name='Bitcoin', is_crypto=True)
        
        # Billetera con 0 USD
        self.usd_wallet = Wallet.objects.create(user=self.user, asset=self.usd, balance=0)

    def test_cannot_buy_without_funds(self):
        """Prueba REAL: El servicio debe impedir comprar si no hay dinero"""
        
        # Intentamos comprar 1 BTC a 50,000 USD
        with pytest.raises(ValueError) as excinfo:
            OrderService.create_order(
                user=self.user,
                asset_code='BTC',
                side='BUY',
                amount=1.0,
                price=50000.0
            )
        
        # Verificamos que el mensaje de error sea el correcto
        assert "Saldo insuficiente" in str(excinfo.value)

    def test_successful_buy_order(self):
        """Prueba REAL: Si hay dinero, la orden se crea y se descuenta el saldo"""
        
        # 1. Le damos dinero al usuario (Trampa divina para el test)
        self.usd_wallet.balance = Decimal('60000.00')
        self.usd_wallet.save()

        # 2. Ejecutamos la compra (1 BTC a 50k)
        order = OrderService.create_order(
            user=self.user,
            asset_code='BTC',
            side='BUY',
            amount=1.0,
            price=50000.0
        )

        # 3. Verificaciones (Asserts)
        assert order.pk is not None           # La orden se guardó en BD
        self.usd_wallet.refresh_from_db()     # Recargamos datos de la BD
        assert self.usd_wallet.balance == 10000.00  # 60k - 50k = 10k sobrantes