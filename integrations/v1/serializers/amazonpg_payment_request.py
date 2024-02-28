from _decimal import Decimal

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
    cvv = serializers.SerializerMethodField()
    customer_id = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()

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
        amount = Decimal(data.get('transaction_data').get("amount"))
        return str(round(amount, 2))

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

    def get_cvv(self, data):
        return data.get('request_data').get("cvv")

    def get_customer_id(self, data):
        return data.get('request_data').get("customer_id")

    def get_invoice_id(self, data):
        return data.get('transaction_data').get("invoice_id")

    def get_return_url(self, data):
        app_config = get_app_config()
        params = '?id=' + encrypt_string(data.get('transaction_data').get(
            'transaction_id'))
        return add_payment_gateway_info_in_url(
            transaction_data=data.get('transaction_data'),
            app_config=app_config, params=params,
            code=AMAZONPG_HUB_CODE)


class AmazonPGCardPaymentRequestSerializer(AmazonPGPaymentRequestSerializer):
    token = serializers.SerializerMethodField()
    return_url = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    def get_payment_method(self, data):
        return data.get('request_data').get("payment_method")

    def get_token(self, data):
        return data.get('request_data').get("token")

    def get_return_url(self, data):
        app_config = get_app_config()
        params = '?id=' + encrypt_string(data.get('transaction_data').get(
            'transaction_id'))
        return add_payment_gateway_info_in_url(
            transaction_data=data.get('transaction_data'),
            app_config=app_config, params=params,
            code=AMAZONPG_HUB_CODE)


class AmazonPGApplepayAppleHeaderSerializer(serializers.Serializer):
    apple_transactionId = serializers.SerializerMethodField()
    apple_ephemeralPublicKey = serializers.SerializerMethodField()
    apple_publicKeyHash = serializers.SerializerMethodField()

    def get_apple_transactionId(self, data):
        return data.get('request_data').get("header").get("transactionId")

    def get_apple_ephemeralPublicKey(self, data):
        return data.get('request_data').get("header").get(
            "ephemeralPublicKey")

    def get_apple_publicKeyHash(self, data):
        return data.get('request_data').get("header").get("publicKeyHash")


class AmazonPGApplepayApplePaymentMethodSerializer(serializers.Serializer):
    apple_displayName = serializers.SerializerMethodField()
    apple_network = serializers.SerializerMethodField()
    apple_type = serializers.SerializerMethodField()

    def get_apple_displayName(self, data):
        return data.get('request_data').get("paymentMethod").get(
            "displayName")

    def get_apple_network(self, data):
        return data.get('request_data').get("paymentMethod").get("network")

    def get_apple_type(self, data):
        return data.get('request_data').get("paymentMethod").get("type")


class AmazonPGApplepayPaymentRequestSerializer(
    AmazonPGPaymentRequestSerializer):
    apple_data = serializers.SerializerMethodField()
    apple_signature = serializers.SerializerMethodField()
    apple_header = serializers.SerializerMethodField()
    apple_paymentMethod = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    def get_apple_data(self, data):
        return data.get('request_data').get("data")

    def get_apple_signature(self, data):
        return data.get('request_data').get("signature")

    def get_payment_method(self, data):
        return data.get('request_data').get("payment_method")

    def get_apple_header(self, data):
        return AmazonPGApplepayAppleHeaderSerializer(data).data

    def get_apple_paymentMethod(self, data):
        return AmazonPGApplepayApplePaymentMethodSerializer(data).data


class AmazonPGTokenizationSerializer(serializers.Serializer):
    card_number = serializers.SerializerMethodField()
    expiry_date = serializers.SerializerMethodField()
    card_security_code = serializers.SerializerMethodField()
    card_holder_name = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    remember_me = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()



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

    def get_remember_me(self, data):
        return data.get('request_data').get("remember_me")

    def get_customer_email(self, data):
        return data.get('transaction_data').get('customer_email')
