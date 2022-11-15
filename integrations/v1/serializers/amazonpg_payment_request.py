from rest_framework import serializers

from core.utils import get_app_config


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
    token = serializers.SerializerMethodField()
    return_url = serializers.SerializerMethodField()

    def get_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_customer_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_amount(self, data):
        return str(data.get('transaction_data').get("amount"))

    def get_order_reference(self, data):
        return data.get('transaction_data').get("order_reference")

    def get_customer_name(self, data):
        """
        Method for getting customer name, if customer name is not present
        in transaction data then need to take it from request data
        """
        transaction_data = data.get('transaction_data')
        customer_name = transaction_data.get('customer_name')
        if not customer_name:
            request_data = data.get('request_data')
            customer_name = request_data.get('customer_name', '')
            if not customer_name:
                customer_name = "Not provided"

        return customer_name

    def get_ip(self, data):
        return data.get('transaction_data').get("ip")

    def get_token(self, data):
        return data.get('request_data').get("token")

    def get_return_url(self):
        url = get_app_config().front_end_redirect_url
        return url
