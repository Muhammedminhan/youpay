from rest_framework import serializers

from core.utils import get_app_config, encrypt_string
from integrations.constants import AMAZONPG_HUB_CODE
from services.v1.views.common import add_payment_gateway_info_in_url


class AmazonPGPaymentRequestSerializer(serializers.Serializer):
    currency = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    ip = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    return_url = serializers.SerializerMethodField()

    def get_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_language(self, data):
        return data.get('transaction_data').get("language")

    def get_platform(self, data):
        return data.get('transaction_data').get("platform")

    def get_customer_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_customer_phone(self, data):
        return data.get('transaction_data').get("customer_phone")

    def get_amount(self, data):
        return str(data.get('transaction_data').get("amount"))

    def get_order_reference(self, data):
        return data.get('transaction_data').get("order_reference")

    def get_customer_name(self, data):
        return data.get('transaction_data').get('customer_name')

    def get_ip(self, data):
        return data.get('transaction_data').get("ip")

    def get_token(self, data):
        return data.get('request_data').get("token")

    def get_card_number(self, data):
        return data.get('request_data').get("card_number")

    def get_return_url(self, data):
        url = get_app_config().front_end_domain
        params = '?id=' + encrypt_string(data.get('transaction_data').get(
            'transaction_id'))

        return add_payment_gateway_info_in_url(data.get('transaction_data'),
                                               url, params,
                                               AMAZONPG_HUB_CODE)


class AmazonPGTokenizationSerializer(serializers.Serializer):
    card_number = serializers.SerializerMethodField()
    expiry_date = serializers.SerializerMethodField()
    card_security_code = serializers.SerializerMethodField()
    card_holder_name = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()

    def get_card_number(self, data):
        return data.get('request_data').get("card_number")

    def get_expiry_date(self, data):
        return data.get('request_data').get("expiry_date")

    def get_card_security_code(self, data):
        return data.get('request_data').get("card_security_code")

    def get_card_holder_name(self, data):
        return data.get('request_data').get("card_holder_name")

    def get_order_reference(self, data):
        order_reference = data.get('transaction_data').get('order_reference')
        merchant_reference = order_reference.replace('|', '-')
        return merchant_reference

    def get_language(self, data):
        return data.get('transaction_data').get("language")
