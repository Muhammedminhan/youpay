import string
import random

from rest_framework import serializers


class CreditBalanceSerializer(serializers.Serializer):
    payment_currency = serializers.SerializerMethodField()
    store_currency = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    payment_reference = serializers.SerializerMethodField()

    def get_payment_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_store_currency(self, data):
        return data.get('transaction_data').get("cart_currency")

    def get_user_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_user_phone(self, data):
        return data.get('transaction_data').get("customer_phone")

    def get_platform(self, data):
        return data.get('transaction_data').get("platform")

    def get_payment_reference(self, data):
        order_reference = data.get('transaction_data').get("order_reference")
        reference_string = ''.join(random.choices(string.ascii_uppercase +
                                                  string.digits, k=10))
        payment_reference = order_reference + '-' + reference_string
        return payment_reference
