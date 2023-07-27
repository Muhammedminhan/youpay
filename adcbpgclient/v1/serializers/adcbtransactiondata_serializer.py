from rest_framework import serializers

from adcbpgclient.models import ADCBTransactionData
from integrations.common import WebhookDataFormat


class ADCBTransactionDataSerializer(serializers.ModelSerializer,
                                    WebhookDataFormat):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    amount_in_aed = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    redeemed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    redeemed_points = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    payable_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    available_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    available_points = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)
    redemption_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True)

    class Meta:
        model = ADCBTransactionData
        fields = '__all__'

    def to_internal_value(self, data):
        issuer_bank = self.get_issuer_bank(
            data.get('checkoutpg_response_data'))
        three_ds_check = self.get_three_ds(
            data.get('checkoutpg_response_data'))
        cvv_check = self.get_cvv_check(data.get('checkoutpg_response_data'))
        return {
            'issuer_bank': issuer_bank,
            'three_ds_check': three_ds_check,
            'cvv_check': cvv_check
        }
