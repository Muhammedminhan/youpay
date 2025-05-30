from rest_framework import serializers

from core.models import PaymentConfiguration


class PaymentConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentConfiguration
        fields = ('payment_method', 'active', 'guest_user_enabled',
                  'beta_version', 'payment_gateway',
                  'partial_redemption_allowed',
                  'burn_full_redemption_enabled', 'earn_enabled',
                  'earn_on_partial_redemption')
