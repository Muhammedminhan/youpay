import requests
import json
import logging

from django.conf import settings
from rest_framework import status

from integrations.constants import (CHECKOUTPG_PAYMENT_CONFIGURATIONS,
                                    CHECKOUTPG_CONFIG_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT)

logger = logging.getLogger(__name__)


class CheckoutpgManager(object):

    def __int__(self):
        pass

    def get_checkout_payment_data(self):
        # TODO - params: uuid(payment)
        # {
        #     "currency": "AED",
        #     "token_type": "card",
        #     "customer_email": "jomon@yougotagift.com",
        #     "is_save_user_token": "false",
        #     "response_url": "http://192.168.225.227:12000/checkout/invoices/31551/orders/22879/webloading/",
        #     "cvv": "",
        #     "amount": "100.0000",
        #     "card_type": "",
        #     "order_reference": "Invoice-31551|ygag|VZMyp-R16CVLqntTjd9YI",
        #     "token": "tok_2fljwtdb3ipe7digcwmkmsd56u",
        #     "channel_code": "YGAGAE",
        #     "invoice_pk": "31551",
        #     "customer_ip_address": "84.226.122.71",
        #     "customer_name": "jomon_loc"
        # }
        pass

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
        channel_codes = []
        channel_code = CHECKOUTPG_PAYMENT_CONFIGURATIONS.get(
            currency.upper())
        channel_codes.append(channel_code)

        params = {'channel_code': channel_codes}
        headers = {'Api-key': settings.CHECKOUTPG_API_KEY}
        URL = settings.CHECKOUTPG_DOMAIN + CHECKOUTPG_CONFIG_ENDPOINT_V2
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
                    return data, resp_status
                return message, resp_status
            logger.error("Unable to fetch Checkoutpg configurations.")
            return None, None
        except Exception as e:
            logger.error("Failed to fetch the checkoutpg v2 configuration "
                         "data {}".format(e))
            return None, None

    def get_saved_cards(self, email, currency):
        """
        Method for getting saved cards
        """
        saved_cards = []
        try:
            PARAMS = {'key': settings.CHECKOUTPG_API_KEY,
                      'email': email,
                      'currency': currency}
            URL = settings.CHECKOUTPG_DOMAIN + CHECKOUTPG_SAVED_CARD_ENDPOINT_V2
            saved_cards = requests.get(url=URL, params=PARAMS)
            if saved_cards:
                saved_cards = json.loads(saved_cards.text).get('cards')
        except Exception as e:
            logger.error("Unable to fetch saved card details for user {0} "
                         "because, {1}".format(email, str(e)))
        return saved_cards

    def delete_saved_card(self, card_id):
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

    def saved_card_payment(self, data):
        # TODO
        #  - data: uuid, request data, token
        pass

    def card_payemnt(self, payment_id):
        pass
