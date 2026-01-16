from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import OrderService
from .models import Wallet
from .serializers import OrderCreateSerializer, WalletSerializer
from django.shortcuts import render
from django.core.cache import cache
from django.http import HttpResponse

class PortfolioView(APIView):
    """GET /api/portfolio/ -> Devuelve tus saldos"""

    def get(self, request):
        # En un caso real usaríamos request.user, aquí forzamos al usuario 'admin'
        # o 'trader' para simplificar pruebas sin sistema de login complejo aún.
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.first()

        wallets = Wallet.objects.filter(user=user)
        serializer = WalletSerializer(wallets, many=True)
        return Response(serializer.data)


class CreateOrderView(APIView):
    """POST /api/orders/ -> Crea una orden de compra/venta"""

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Datos limpios y validados
            data = serializer.validated_data

            # Obtenemos el usuario (Hardcodeado al primero para pruebas rápidas)
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.first()

            try:
                # LLAMAMOS A TU LÓGICA SEGURA
                order = OrderService.create_order(
                    user=user,
                    asset_code=data["asset_code"],
                    side=data["side"],
                    amount=data["amount"],
                    price=data["price"],
                )

                return Response(
                    {
                        "status": "success",
                        "order_id": order.id,
                        "message": f"Orden {order.side} creada correctamente",
                    },
                    status=status.HTTP_201_CREATED,
                )

            except ValueError as e:
                # Capturamos el error "Saldo insuficiente" y lo devolvemos bonito
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def dashboard_view(request):
    """Vista principal para el usuario normal (Renderiza HTML)"""
    # Truco temporal: Usamos el primer usuario para probar sin sistema de login
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.first()
    
    # Obtenemos sus billeteras
    wallets = Wallet.objects.filter(user=user)
    usd_wallet = wallets.filter(asset__code='USD').first()
    btc_wallet = wallets.filter(asset__code='BTC').first()
    
    context = {
        'usd_balance': usd_wallet.balance if usd_wallet else 0,
        'btc_balance': btc_wallet.balance if btc_wallet else 0,
        'user': user
    }
    return render(request, 'trading/dashboard.html', context)


def price_htmx_view(request):
    """Devuelve solo el número del precio para actualizar la caja"""
    # Intentamos obtener el precio de Redis (que actualiza Celery)
    price = cache.get('btc_price')
    if price is None:
        price = "OFFLINE"
    else:
        # Formateamos como moneda
        price = f"${price:,.2f}"
        
    return HttpResponse(price)

def create_order_htmx_view(request):
    """Procesa el formulario y devuelve un mensaje HTML"""
    # Truco temporal de usuario
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.first()
    
    if request.method == 'POST':
        asset_code = request.POST.get('asset_code')
        side = request.POST.get('side')
        amount = request.POST.get('amount')
        price = request.POST.get('price')

        try:
            OrderService.create_order(
                user=user,
                asset_code=asset_code,
                side=side,
                amount=amount,
                price=price
            )
            # Si sale bien, devolvemos mensaje verde estilo consola
            return HttpResponse('<div class="text-green-500">> SUCCESS: Order executed successfully.</div>')
            
        except ValueError as e:
            # Si falla (ej. saldo insuficiente), mensaje rojo
            return HttpResponse(f'<div class="text-hackerRed">> ERROR: {str(e)}</div>')
            
    return HttpResponse('')