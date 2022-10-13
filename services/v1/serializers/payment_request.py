from rest_framework import serializers

from services.models import PaymentRequestData


def amount_validator(amount):
    if amount < 0:
        raise serializers.ValidationError("Amount must be positive")
    return amount


class PaymentRequestDataSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=4,
                                      validators=[amount_validator])

    class Meta:
        model = PaymentRequestData
        fields = '__all__'


class PaymentVerifyDataSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
    invoice_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=4,
                                      validators=[amount_validator])
    currency = serializers.CharField()
