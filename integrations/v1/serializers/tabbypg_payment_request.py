from rest_framework import serializers

from core.utils import get_app_config
from integrations.constants import TABBYPG_HUB_CODE
from services.v1.views.common import add_payment_gateway_info_in_url


def validate_tabby_amount(data):
    print("Data in validate_tabby_amount", data)
    # in case of SAR currency, amount should between 1 and 1500
    # if data.get('amount') < 0 or data.get('amount') > 1500:
    #     raise serializers.ValidationError(
    #         {'amount': 'Amount should be in range 0 to 1500'})


class TabbyPGRequestValidator(serializers.Serializer):
    amount = serializers.DecimalField(decimal_places=4, max_digits=12,
                                      validators=[validate_tabby_amount])

    # amount
    pass


class TabbyPGPaymentRequestSerializer(serializers.Serializer):
    currency = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    payment_reference = serializers.SerializerMethodField()

    loyalty_level = serializers.SerializerMethodField()
    registered_since = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    order_items = serializers.SerializerMethodField()
    order_history = serializers.SerializerMethodField()

    customer_email = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_ip_address = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

    cancel_url = serializers.SerializerMethodField()
    failure_url = serializers.SerializerMethodField()
    success_url = serializers.SerializerMethodField()

    def get_currency(self, data):
        return data.get('transaction_data').get("currency")

    def get_amount(self, data):
        amount = float(data.get('transaction_data').get("amount"))
        currency = data.get('transaction_data').get("currency")
        if currency == "SAR":
            if amount < 0 or amount > 750:
                raise serializers.ValidationError(
                    {
                        'amount': 'SAR Amount should be in range 0 to 750, provided amount is {}'.format(
                            amount)})

        elif currency == "AED":
            if amount < 0 or amount > 1500:
                raise serializers.ValidationError(
                    {
                        'amount': 'AED Amount should be in range 0 to 1500, provided amount is {}'.format(
                            amount)})

        return amount

    def get_order_reference(self, data):
        return data.get('transaction_data').get("order_reference")

    def get_invoice_id(self, data):
        return data.get('transaction_data').get("invoice_id")

    def get_payment_reference(self, data):
        return data.get('transaction_data').get("payment_reference")

    def get_loyalty_level(self, data):
        loyalty_level = data.get("loyalty_level")
        if loyalty_level:
            return int(data.get("loyalty_level"))
        else:
            return 0

    def get_registered_since(self, data):
        return data.get('transaction_data').get("registered_since")

    def get_language(self, data):
        return data.get("language")

    def get_platform(self, data):
        return data.get('transaction_data').get("platform")

    def get_order_items(self, data):
        return data.get('transaction_data').get("order_items")

    def get_order_history(self, data):
        return data.get('transaction_data').get("order_history")

    def get_customer_email(self, data):
        return data.get('transaction_data').get("customer_email")

    def get_customer_name(self, data):
        return data.get('transaction_data').get("customer_name")

    def get_customer_ip_address(self, data):
        return data.get('transaction_data').get("ip")

    def get_customer_phone(self, data):
        return data.get('transaction_data').get("customer_phone")

    def get_cancel_url(self, data):
        return common_response_url(data)

    def get_failure_url(self, data):
        return common_response_url(data)

    def get_success_url(self, data):
        return common_response_url(data)


def common_response_url(data):
    url = get_app_config().front_end_redirect_url
    params = '?id=' + data.get('transaction_data').get(
        'transaction_id')

    return add_payment_gateway_info_in_url(url, params,
                                           TABBYPG_HUB_CODE)
