import logging
import random
import string

from rest_framework import serializers

from integrations.constants import CITI_CLIENT_CODE

logger = logging.getLogger(__name__)


class GenerateOTPRequestSerializer(serializers.Serializer):
    reference_id = serializers.SerializerMethodField()
    request_id = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone_code = serializers.SerializerMethodField()
    customer_phone_number = serializers.SerializerMethodField()
    card_last4 = serializers.SerializerMethodField()
    redemption_partner = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

    def get_reference_id(self, data):
        random_payment_reference = (
            ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=10)))
        return random_payment_reference

    def get_request_id(self, data):
        random_request_id = (
            ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=10)))
        return random_request_id

    def get_customer_name(self, data):
        return data.get('transaction_data', {}).get('customer_name')

    def get_redemption_partner(self, data):
        return CITI_CLIENT_CODE

    def get_invoice_id(self, data):
        return data.get('transaction_data', {}).get('invoice_id')

    def get_platform(self, data):
        return data.get('transaction_data', {}).get('platform')

    def get_customer_phone_code(self, data):
        return data.get('request_data', {}).get('phone_country_code')

    def get_customer_phone_number(self, data):
        return data.get('request_data', {}).get('phone_number')

    def get_customer_phone(self, data):
        return data.get('request_data', {}).get('customer_phone')

    def get_card_last4(self, data):
        return data.get('request_data', {}).get('card_last4')

    def get_amount(self, data):
        return str(data.get('transaction_data').get("amount"))

    def get_currency(self, data):
        return data.get('transaction_data', {}).get('currency')

    def get_customer_email(self, data):
        return data.get('transaction_data', {}).get('customer_email')
