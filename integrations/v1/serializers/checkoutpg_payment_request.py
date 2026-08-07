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
    amount_in_aed = serializers.SerializerMethodField()
    is_mada = serializers.SerializerMethodField()
    client_code = serializers.SerializerMethodField()
    customer_uid = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    expiry_month = serializers.SerializerMethodField()
    expiry_year = serializers.SerializerMethodField()

    def get_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_customer_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_amount(self, data):
        amount = (str(data.get('additional_total_amount')) if
                  data.get('additional_total_amount') else
                  str(data.get('transaction_data').get("amount")))
        return amount

    def get_order_reference(self, data):
        return data.get('transaction_data').get("order_reference")
    
    def get_customer_uid(self, data):
        return data.get('transaction_data').get("customer_uid")

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
        app_config = get_app_config()
        params = '?id=' + encrypt_string(
            data.get('transaction_data').get(
                'transaction_id'))

        return add_payment_gateway_info_in_url(
            transaction_data=data.get('transaction_data'),
            app_config=app_config, params=params,
            code=CHECKOUTPG_HUB_CODE)

    def get_card_type(self, data):
        is_mada = data.get('request_data').get("is_mada", False)
        return "mada" if is_mada else ""

    def get_token(self, data):
        return data.get('request_data').get("token")

    def get_channel_code(self, data):
        if data.get('token_type') == 'paypal':
            channel_code = ""
        else:
            checkout_channel_code = data.get(
                'transaction_obj').api_client.checkout_channel_code
            if checkout_channel_code:
                channelcode = checkout_channel_code
            else:
                channelcode = CHECKOUTPG_CHANNEL_CONFIGURATIONS
            channel_code = channelcode.get(
                data.get('transaction_data').get("currency")).get(
                data.get('transaction_data').get("platform").upper())
        return channel_code

    def get_amount_in_aed(self, data):
        """
        method to fetch the amount in aed value from the transaction data
        """
        amount = data.get("transaction_data", {}).get("amount_in_aed")
        if not amount:
            amount = 0
        else:
            amount = str(amount)
        return amount

    def get_client_code(self, data):
        """
        method to fetch client code from the api client
        """
        client_code = data.get("transaction_obj").api_client.client_code
        return client_code

    def get_is_mada(self, data):
        """
        method to fetch is_mada from the request data
        """
        is_mada = data.get('request_data').get("is_mada", False)
        return is_mada

    def get_number(self, data):
        return data.get("request_data").get("number")

    def get_expiry_month(self, data):
        return data.get("request_data").get("expiry_month")

    def get_expiry_year(self, data):
        return data.get("request_data").get("expiry_year")


class ApplepayPaymentDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = YouPayTransactionData
        fields = '__all__'
