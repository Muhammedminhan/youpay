from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from core.validators import URLValidator
from integrations.constants import (PAYMENT_MEDIUM_IOS, PAYMENT_MEDIUM_WEB,
                                    PAYMENT_MEDIUM_MOBILE_WEB,
                                    PAYMENT_MEDIUM_ANDROID)
from integrations.models import PaymentGateway, PaymentConfiguration
from services.constants import CURRENCY_UAE, CURRENCY_KSA
from services.models import APIClient
from core.models import Country, CheckoutFont

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


class APIClientRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True)
    is_client_active = serializers.BooleanField(required=False)
    client_domain = serializers.CharField(max_length=100, required=True,
                                          validators=[URLValidator()])
    logo_file = serializers.ImageField(required=False, allow_null=True)
    mobile_logo_file = serializers.ImageField(required=False, allow_null=True)
    brand_details_path = serializers.CharField(max_length=100, required=False,
                                               allow_blank=True)
    show_aed_equivalent_amount = serializers.BooleanField(required=False)
    currency_channel_config = serializers.JSONField(required=True)
    payment_method = serializers.ListField(required=True,
        child=serializers.CharField())
    product_code = serializers.CharField(max_length=12, required=True)
    allowed_payment_countries = serializers.ListField(required=True,
        child=serializers.CharField())
    font = serializers.PrimaryKeyRelatedField(
        queryset=CheckoutFont.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    def validate_payment_method(self, value):
        for payment_method in value:
            try:
                PaymentConfiguration.objects.get(
                    payment_method=payment_method, active=True)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f"No active payment configuration found for payment "
                    f"method '{payment_method}'"
                )
        return value

    def validate_currency_channel_config(self, value):
        allowed_currencies = {CURRENCY_UAE, CURRENCY_KSA}
        allowed_platforms = {PAYMENT_MEDIUM_IOS, PAYMENT_MEDIUM_WEB,
                             PAYMENT_MEDIUM_MOBILE_WEB,
                             PAYMENT_MEDIUM_ANDROID}

        for currency, channels in value.items():
            if currency not in allowed_currencies:
                raise serializers.ValidationError(
                    f"Unsupported currency: {currency}"
                )

            if not isinstance(channels, dict):
                raise serializers.ValidationError(
                    f"Channels must be a dictionary for {currency}"
                )

            for platform, channel in channels.items():
                if platform not in allowed_platforms:
                    raise serializers.ValidationError(
                        f"Invalid platform '{platform}' for currency "
                        f"'{currency}'"
                    )

                if not isinstance(channel, str) or not channel.strip():
                    raise serializers.ValidationError(
                        f"Channel code must be a non-empty string for "
                        f"{currency} - {platform}"
                    )
        return value

    def validate_allowed_payment_countries(self, value):
        for country_code in value:
            try:
                Country.objects.get(iso_code=country_code)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f"Country with code '{country_code}' does not exist"
                )
        return value

    def validate_client_domain(self, value):
        if not value.endswith('/'):
            value += '/'
        return value


class APIClientResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIClient
        fields = ('name', 'api_key', 'api_secret', 'webhook_url')
