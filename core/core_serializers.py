from rest_framework import serializers

from core.models import PaymentConfiguration


class PaymentConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentConfiguration
        fields = '__all__'
