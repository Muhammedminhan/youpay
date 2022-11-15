from rest_framework import serializers
from integrations.constants import ADCB_CLIENT_CODE

class PointBalanceRequestSerializer(serializers.Serializer):
    card_no = serializers.SerializerMethodField()
    expiry = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    client_code = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    def get_card_no(self, data):
        return data.get('data', {}).get('card_no')

    def get_expiry(self, data):
        return data.get('data', {}).get('expiry')
    def get_customer_name(self, data):
        return data.get('transaction_data', {}).get('customer_name')

    def get_client_code(self, data):
        return ADCB_CLIENT_CODE

    def get_invoice_id(self, data):
        return data.get('transaction_data', {}).get('invoice_id')

    def get_platform(self, data):
        return data.get('transaction_data', {}).get('platform')
