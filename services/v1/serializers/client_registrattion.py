from rest_framework import serializers

from core.validators import URLValidator
from integrations.models import PaymentGateway
from services.models import APIClient


class APIClientRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, required=True)
    webhook_url = serializers.CharField(max_length=255, required=True,
                                        validators=[URLValidator()])
    client_domain = serializers.CharField(max_length=255, required=True,
                                          validators=[URLValidator()])

    class Meta:
        model = APIClient
        fields = '__all__'


class APIClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIClient
        fields = '__all__'


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = '__all__'
