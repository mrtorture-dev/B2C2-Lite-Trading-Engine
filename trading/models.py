# Create your models here.
from django.db import models
from django.conf import settings


class Asset(models.Model):
    """Monedas disponibles (BTC, ETH, USD)"""

    code = models.CharField(max_length=10, unique=True)  # Ej: BTC
    name = models.CharField(max_length=100)  # Ej: Bitcoin
    is_crypto = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class Wallet(models.Model):
    """Billetera del usuario. Una por cada moneda."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)
    balance = models.DecimalField(max_digits=18, decimal_places=8, default=0)

    class Meta:
        unique_together = (
            "user",
            "asset",
        )  # Un usuario no puede tener 2 wallets de BTC

    def __str__(self):
        return f"{self.user.username} - {self.asset.code}: {self.balance}"


class Order(models.Model):
    """Orden de compra/venta"""

    SIDE_CHOICES = (("BUY", "Buy"), ("SELL", "Sell"))
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("FILLED", "Filled"),
        ("CANCELLED", "Cancelled"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)  # Qué compro/vendo
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    initial_amount = models.DecimalField(max_digits=18, decimal_places=8)
    price = models.DecimalField(
        max_digits=18, decimal_places=8, null=True, blank=True
    )  # Para Limit Orders
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.side} {self.initial_amount} {self.asset.code}"


class Trade(models.Model):
    """
    Registro del Match: Une una orden de compra con una de venta.
    """
    # Pata 1: La orden que compró
    buy_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='buy_trades')
    
    # Pata 2: La orden que vendió
    sell_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='sell_trades')
    
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    price = models.DecimalField(max_digits=18, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match: {self.amount} {self.buy_order.asset.code} @ {self.price}"
