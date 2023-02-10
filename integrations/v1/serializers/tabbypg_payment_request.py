import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)
from core.utils import (
    get_app_config, encrypt_string, get_payment_gateway_config)
from core.exceptions import ValidationFailed
from integrations.constants import TABBYPG_HUB_CODE, TABBYPG_CACHE_KEY
from services.v1.views.common import add_payment_gateway_info_in_url


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

        payment_gateway = get_payment_gateway_config(TABBYPG_CACHE_KEY,
                                                     TABBYPG_HUB_CODE)
        if payment_gateway.validation_json:

            # check the currency is in payment_gateway.validation_json
            if currency not in payment_gateway.validation_json.keys():
                raise ValidationFailed(
                    "Currency is not in payment_gateway.validation_json, "
                    "supported currencies are: {}".format(
                        list(payment_gateway.validation_json.keys())))

            currency_dict = payment_gateway.validation_json.get(currency)

            # check the min_amount, max_amount are there in currency_dict
            if ("min_amount" not in currency_dict.keys() or
                    "max_amount" not in currency_dict.keys()):
                raise ValidationFailed(
                    "min_amount or max_amount keys are not in "
                    "payment_gateway.validation_json")

            min_limit = float(currency_dict['min_amount'])
            max_limit = float(currency_dict['max_amount'])

            if amount < min_limit or amount > max_limit:
                raise ValidationFailed(
                    "Amount {} {} should be between {} and"
                    " {}".format(amount, currency, min_limit, max_limit))
        else:
            logger.info("Amount validation not set for payment gateway {}"
                        "".format(payment_gateway.gateway_name))

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
        transaction_id = data.get('transaction_data').get(
            "transaction_id")
        cancel_url = (data.get('transaction_data').get("cancel_url") +
                      '?transaction_id=' + transaction_id)
        return cancel_url

    def get_failure_url(self, data):
        return common_response_url(data)

    def get_success_url(self, data):
        return common_response_url(data)


def common_response_url(data):
    url = get_app_config().front_end_redirect_url
    params = '?id=' + encrypt_string(data.get('transaction_data').get(
        'transaction_id'))

    return add_payment_gateway_info_in_url(url, params,
                                           TABBYPG_HUB_CODE)
