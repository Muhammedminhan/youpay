from rest_framework import serializers

from core.utils import encrypt_string
from core.utils import get_app_config
from integrations.constants import (ADCB_CLIENT_CODE, B2CPAYBACK_HUB_CODE,
                                    ADCB_TOKEN_TYPE, ADCB_REDEMPTION_CURRENCY,
                                    CHECKOUT_UAE_CHANNEL_CODE,
                                    AMAZONPG_HUB_CODE)
from services.v1.views.common import add_payment_gateway_info_in_url


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
        return data.get('data', {}).get('name_on_card')

    def get_client_code(self, data):
        return ADCB_CLIENT_CODE

    def get_invoice_id(self, data):
        return data.get('transaction_data', {}).get('invoice_id')

    def get_platform(self, data):
        return data.get('transaction_data', {}).get('platform')


class AuthenticateRequestSerializer(serializers.Serializer):
    is_save_user_token = serializers.SerializerMethodField()
    client_code = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    invoice_amount = serializers.SerializerMethodField()
    channel_code = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    customer_ip_address = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    reference_id = serializers.SerializerMethodField()
    token_type = serializers.SerializerMethodField()
    card_type = serializers.SerializerMethodField()
    redemption_currency = serializers.SerializerMethodField()
    selected_amount = serializers.SerializerMethodField()
    checkout_amount = serializers.SerializerMethodField()
    response_url = serializers.SerializerMethodField()
    amount_in_aed = serializers.SerializerMethodField()
    invoice_currency = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()

    def get_is_save_user_token(self, data):
        return False

    def get_client_code(self, data):
        return ADCB_CLIENT_CODE

    def get_platform(self, data):
        return data.get('transaction_data', {}).get('platform')

    def get_invoice_amount(self, data):
        return str(data.get('transaction_data', {}).get('amount'))

    def get_channel_code(self, data):
        if float(data.get('data', {}).get('checkout_amount')) > 0:
            return CHECKOUT_UAE_CHANNEL_CODE
        return data.get('transaction_data', {}).get('channel_code')

    def get_invoice_id(self, data):
        return data.get('transaction_data', {}).get('invoice_id')

    def get_customer_ip_address(self, data):
        return data.get('transaction_data', {}).get('ip')

    def get_customer_email(self, data):
        return data.get('transaction_data', {}).get('customer_email')

    def get_reference_id(self, data):
        return data.get('data', {}).get('reference_id')

    def get_token_type(self, data):
        return ADCB_TOKEN_TYPE

    def get_card_type(self, data):
        return data.get('data', {}).get('card_type')

    def get_redemption_currency(self, data):
        return ADCB_REDEMPTION_CURRENCY

    def get_selected_amount(self, data):
        return data.get('data', {}).get('selected_amount')

    def get_checkout_amount(self, data):
        return data.get('data', {}).get('checkout_amount')

    def get_response_url(self, data):
        app_config = get_app_config()
        params = '?id=' + encrypt_string(data.get('transaction_data', {}).get(
            'transaction_id')) + '&redemption_reference_id=' + data.get(
            'data', {}).get('reference_id')

        return add_payment_gateway_info_in_url(
            transaction_data=data.get('transaction_data'),
            app_config=app_config, params=params,
            code=B2CPAYBACK_HUB_CODE)

    def get_amount_in_aed(self, data):
        return str(data.get('transaction_data', {}).get('amount'))

    def get_invoice_currency(self, data):
        return ADCB_REDEMPTION_CURRENCY

    def get_order_reference(self, data):
        return str(data.get('transaction_data', {}).get('order_reference'))


class AuthenticateRequestAmazonSerializer(serializers.Serializer):
    currency = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    response_url = serializers.SerializerMethodField()
    selected_amount = serializers.SerializerMethodField()
    checkout_amount = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    reference_id = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    customer_ip_address = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    cvv = serializers.SerializerMethodField()
    gateway = serializers.SerializerMethodField()

    def get_currency(self, data):
        return str(data.get('transaction_data', {}).get('currency'))

    def get_card_number(self, data):
        return data.get('data', {}).get('card_number')

    def get_customer_email(self, data):
        return str(data.get('transaction_data', {}).get('customer_email'))

    def get_response_url(self, data):
        app_config = get_app_config()
        params = '?id=' + encrypt_string(data.get('transaction_data').get(
            'transaction_id'))
        return add_payment_gateway_info_in_url(
            transaction_data=data.get('transaction_data'),
            app_config=app_config, params=params,
            code=AMAZONPG_HUB_CODE)

    def get_selected_amount(self, data):
        return data.get('data', {}).get('selected_amount')

    def get_checkout_amount(self, data):
        return data.get('data', {}).get('checkout_amount')

    def get_order_reference(self, data):
        return str(data.get('transaction_data', {}).get('order_reference'))

    def get_reference_id(self, data):
        return data.get('data', {}).get('reference_id')

    def get_invoice_id(self, data):
        return data.get('transaction_data', {}).get('invoice_id')

    def get_customer_ip_address(self, data):
        return data.get('transaction_data', {}).get('ip')

    def get_language(self, data):
        return data.get('transaction_data', {}).get('language')

    def get_platform(self, data):
        return data.get('transaction_data', {}).get('ip')

    def get_payment_method(self, data):
        return data.get('data', {}).get('payment_method')

    def get_cvv(self, data):
        return data.get('data', {}).get('cvv')

    def get_gateway(self, data):
        return data.get('data', {}).get('gateway')
