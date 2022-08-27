from rest_framework import serializers

from core.validators import MinLengthValidator, URLValidator
from services.models import APIClient, PaymentRequestData


class APIClientRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, required=True)
    api_key = serializers.CharField(max_length=255, required=True,
                                    validators=[MinLengthValidator(20)])
    endpoint_url = serializers.CharField(max_length=255, required=True,
                                         validators=[URLValidator()])
    client_domain = serializers.CharField(max_length=255, required=True,
                                          validators=[URLValidator()])

    class Meta:
        model = APIClient
        fields = '__all__'


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
