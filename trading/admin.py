from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.core.management import call_command
from django.contrib import messages
from .models import Wallet, Order, Trade, Asset

# --- PERSONALIZACIÓN DEL ADMIN DE ASSETS ---
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_crypto')
    list_filter = ('is_crypto',)
    search_fields = ('code', 'name')
    
    # Inyectamos el template personalizado (que crearemos en el paso 3.2)
    change_list_template = "admin/trading/asset/change_list.html"

    def get_urls(self):
        """Agregamos una URL personalizada para el botón de sync"""
        urls = super().get_urls()
        custom_urls = [
            path('sync-binance/', self.admin_site.admin_view(self.sync_assets_view), name='sync-binance'),
        ]
        return custom_urls + urls

    def sync_assets_view(self, request):
        """Esta función se ejecuta al dar clic al botón"""
        try:
            # Llamamos al comando mágico que creaste
            call_command('sync_assets')
            self.message_user(request, "✅ SUCCESS: Binance Assets Synced Successfully", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ ERROR: {str(e)}", level=messages.ERROR)
            
        # Redirigimos de vuelta a la lista de assets
        return HttpResponseRedirect("../")

# --- RESTO DE LOS MODELOS (Sin cambios) ---
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'balance')
    list_filter = ('asset',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'side', 'initial_amount', 'price', 'status', 'created_at')
    list_filter = ('side', 'status', 'asset')

# ... (Todo lo de arriba del AssetAdmin déjalo igual) ...

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    # AQUÍ ESTÁ LA CLAVE: Agregamos 'show_buyer' y 'show_seller' a la lista
    list_display = ('id', 'show_buyer', 'show_seller', 'amount', 'price', 'timestamp')
    
    list_filter = ('timestamp',)
    # Buscador: permite buscar por nombre del usuario comprador o vendedor
    search_fields = ('buy_order__user__username', 'sell_order__user__username')

    # Función para mostrar quién compró (Long)
    @admin.display(description='Buyer (Long)')
    def show_buyer(self, obj):
        # Accedemos a la relación: Trade -> Buy Order -> User -> Username
        return f"{obj.buy_order.user.username} ({obj.buy_order.asset.code})"

    # Función para mostrar quién vendió (Short)
    @admin.display(description='Seller (Short)')
    def show_seller(self, obj):
        # Accedemos a la relación: Trade -> Sell Order -> User -> Username
        return f"{obj.sell_order.user.username} ({obj.sell_order.asset.code})"
