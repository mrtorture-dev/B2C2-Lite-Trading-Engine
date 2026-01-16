from rest_framework import serializers
from .models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source="asset.code")

    class Meta:
        model = Wallet
        fields = ["asset_code", "balance"]


class OrderCreateSerializer(serializers.Serializer):
    """
    Valida los datos que nos envían para crear una orden.
    No usamos ModelSerializer aquí porque queremos controlar
    manualmente qué datos entran al OrderService.
    """

    asset_code = serializers.CharField(max_length=10)
    side = serializers.ChoiceField(choices=["BUY", "SELL"])
    amount = serializers.DecimalField(max_digits=18, decimal_places=8)
    price = serializers.DecimalField(max_digits=18, decimal_places=8)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser positiva.")
        return value
