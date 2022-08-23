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


class PaymentRequestDataSerializer(serializers.ModelSerializer):
    # order = OrderSerializer()
    api_client = serializers.CharField(required=True)

    class Meta:
        model = PaymentRequestData
        fields = '__all__'
