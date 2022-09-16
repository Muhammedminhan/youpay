import json
import logging

import requests
from django.conf import settings
from rest_framework import status

from integrations.constants import (CHECKOUTPG_PAYMENT_CONFIGURATIONS,
                                    CHECKOUTPG_CONFIG_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_ENDPOINT)
from .utils import get_transaction_object
from core.utils import get_checkoutpg_config
from core.response_messages import YouPayResponse
from integrations.messages import CHECKOUTPG_CONNECTION_ERROR_MESSAGE

logger = logging.getLogger(__name__)


class CheckoutpgManager(object):
    checkoutpg_config = get_checkoutpg_config()
    response_obj = YouPayResponse()

    def get_checkout_payment_data(self, data):
        # TODO - params: uuid(payment)
        #  - from api should get token type,

        payment_data = {
            "currency": data.get('transaction_data').get("currency"),
            "customer_email": data.get('transaction_data').get(
                "customer_email"),
            "amount": data.get('transaction_data').get("amount"),
            "order_reference": data.get('transaction_data').get(
                "order_reference"),
            "invoice_pk": data.get('transaction_data').get("invoice_id"),

            "cvv": data.get('request_data').get("cvv"),
            "customer_name": data.get('request_data').get("customer_name"),
            "customer_ip_address": data.get('request_data').get(
                "customer_ip_address"),

            "token_type": data.get("token_type"),

            "is_save_user_token": "false",  # todo based on the token type
            "response_url": "http://192.168.225.227:12000/checkout/invoices/31551/orders/22879/webloading/",
            # TODO prepare url
            "card_type": "",  # TODO get it from transaction_object
            "token": "tok_2fljwtdb3ipe7digcwmkmsd56u",
            # TODO get it from transaction_object
            "channel_code": "YGAGAE",  # TODO get it from transaction_object
        }
        return json.dumps(payment_data)

    def get_payment_header(self):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': settings.CHECKOUTPG_API_KEY,
            'Api-key': settings.CHECKOUTPG_API_KEY
        }
        return headers

    def get_configuratoins(self, currency):
        """
        Method for getting configurations
        params: currency
        response: json response from the checkoutpg
        """
        if self.checkoutpg_config:
            channel_codes = []
            channel_code = CHECKOUTPG_PAYMENT_CONFIGURATIONS.get(
                currency.upper())
            channel_codes.append(channel_code)

            params = {'channel_code': channel_codes}
            headers = {'Api-key': self.checkoutpg_config.api_key}
            URL = self.checkoutpg_config.domain + CHECKOUTPG_CONFIG_ENDPOINT_V2
            try:
                configurations = requests.get(url=URL, params=params,
                                              headers=headers)
                if configurations:
                    response = json.loads(configurations.text)
                    resp_status = response.get('status', False)
                    message = response.get('message', None)
                    if response and resp_status == status.HTTP_200_OK:
                        public_keys = response.get('public_keys', None)
                        checkout_mada_bins = response.get('card_bins')[0].get(
                            'bin',
                            []) if response.get(
                            'card_bins', None) else []
                        data = {'public_keys': public_keys,
                                'checkout_mada_bins': checkout_mada_bins}
                        return data, self.response_obj.SUCCESS

                    return message, resp_status
                logger.error("Unable to fetch Checkoutpg configurations.")
                return None, self.response_obj.CHECKOUTPG_CONNECTION_ERROR
            except Exception as e:
                logger.error(
                    "Failed to fetch the checkoutpg v2 configuration "
                    "data {}".format(e))
                return None, self.response_obj.CHECKOUTPG_CONNECTION_ERROR
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.response_obj.CHECKOUTPG_CONNECTION_ERROR

    def get_saved_cards(self, email, currency):
        """
        Method for getting saved cards
        """
        if self.checkoutpg_config:
            saved_cards = []
            try:
                PARAMS = {'key': self.checkoutpg_config.api_key,
                          'email': email,
                          'currency': currency}
                URL = self.checkoutpg_config.domain + CHECKOUTPG_SAVED_CARD_ENDPOINT_V2
                saved_cards = requests.get(url=URL, params=PARAMS)
                if saved_cards:
                    saved_cards = json.loads(saved_cards.text).get('cards')
            except Exception as e:
                logger.error(
                    "Unable to fetch saved card details for user {0} "
                    "because, {1}".format(email, str(e)))
            return saved_cards
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def delete_saved_card(self, card_id):
        checkoutpg_config = get_checkoutpg_config()
        if checkoutpg_config:
            try:
                header = self.get_payment_header()
                URL = (
                        settings.CHECKOUTPG_DOMAIN + CHECKOUTPG_SAVED_CARD_ENDPOINT +
                        card_id + '/')
                response = requests.delete(url=URL, headers=header)
                return json.loads(response.text)
            except Exception as e:
                logger.error(
                    "Unable to delete saved card {0} details because, {1}"
                    .format(card_id, str(e)))
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def saved_card_payment(self, data):
        # TODO
        #  - data: uuid, request data, token
        checkoutpg_config = get_checkoutpg_config()
        if checkoutpg_config:
            success_dict = {}
            payment_data = self.get_checkout_payment_data(data)

            url = settings.CHECKOUTPG_DOMAIN + CHECKOUTPG_PAYMENT_ENDPOINT
            headers = self.get_payment_header()
            response = requests.post(url, data=payment_data,
                                     headers=headers)

            return success_dict
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, None

    def card_payemnt(self, data):
        payment_data = self.get_checkout_payment_data(data)
        return payment_data
