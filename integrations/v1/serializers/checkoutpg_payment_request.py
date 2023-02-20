from rest_framework import serializers

from core.utils import encrypt_string
from core.utils import get_app_config
from integrations.constants import (CHECKOUTPG_CHANNEL_CONFIGURATIONS,
                                    CHECKOUTPG_HUB_CODE)
from payments.models import YouPayTransactionData
from services.v1.views.common import add_payment_gateway_info_in_url


class CheckoutPaymentRequestSerializer(serializers.Serializer):
    currency = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    invoice_pk = serializers.SerializerMethodField()
    cvv = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_ip_address = serializers.SerializerMethodField()
    token_type = serializers.SerializerMethodField()
    is_save_user_token = serializers.SerializerMethodField()
    response_url = serializers.SerializerMethodField()
    card_type = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    channel_code = serializers.SerializerMethodField()

    def get_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_customer_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_amount(self, data):
        return str(data.get('transaction_data').get("amount"))

    def get_order_reference(self, data):
        return data.get('transaction_data').get("order_reference")

    def get_invoice_pk(self, data):
        return data.get('transaction_data').get("invoice_id")

    def get_cvv(self, data):
        return data.get('request_data').get("cvv")

    def get_customer_name(self, data):
        """
        Method for getting customer name, ie Taking card name as customer name
         if provided else take from transaction data
        """

        request_data = data.get('request_data')

        customer_name = request_data.get('customer_name', '')
        if customer_name == "":
            transaction_data = data.get('transaction_data')
            customer_name = transaction_data.get("customer_name",
                                                 "Not Provided")

        return customer_name

    def get_customer_ip_address(self, data):
        return data.get('transaction_data').get("ip")

    def get_token_type(self, data):
        return data.get('token_type')

    def get_is_save_user_token(self, data):
        """
        Method for getting is_save_user_token, True or False will be returned
        """
        return data.get('request_data').get("is_save_user_token", False)

    def get_response_url(self, data):
        url = get_app_config().front_end_redirect_url
        params = '?id=' + encrypt_string(data.get('transaction_data').get(
            'transaction_id'))
        return add_payment_gateway_info_in_url(url, params,
                                               CHECKOUTPG_HUB_CODE)

    def get_card_type(self, data):
        return ""

    def get_token(self, data):
        return data.get('request_data').get("token")

    def get_channel_code(self, data):
        if data.get('token_type') == 'paypal':
            channel_code = ""
        else:
            channel_code = CHECKOUTPG_CHANNEL_CONFIGURATIONS.get(
                data.get('transaction_data').get("currency")).get(
                data.get('transaction_data').get("platform").upper())
        return channel_code


class ApplepayPaymentDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = YouPayTransactionData
        fields = [
            'transaction_id',
            'amount',
            'currency',
            'invoice_id',
            'order_reference',
            'success_url',
            'failure_url',
            'cancel_url',
            'verify_url',
            'amount',
            'ip',
            'customer_email',
            'customer_name',
        ]
