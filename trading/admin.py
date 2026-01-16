from django.contrib import admin
from .models import Asset, Wallet, Order, Trade


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_crypto")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "balance")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("user", "side", "asset", "initial_amount", "status")


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "price", "timestamp")
