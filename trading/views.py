from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import OrderService
from .models import Wallet
from .serializers import OrderCreateSerializer, WalletSerializer


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
