import json
import logging

import requests
from django.conf import settings
from rest_framework import status

from core.constants import PAYMENT_GATEWAY_CHECKOUTPG
from core.response_messages import YouPayResponse
from core.utils import get_checkoutpg_config
from integrations.constants import (CHECKOUTPG_PAYMENT_CONFIGURATIONS,
                                    CHECKOUTPG_CONFIG_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_VERIFICATION_ENDPOINT)
from integrations.messages import CHECKOUTPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.checkoutpg_payment_request import (
    CheckoutPaymentRequestSerializer)
from payments.constants import (PAYMENT_STATUS_PENDING,
                                PAYMENT_METHOD_SAVED_CARD)
from services.v1.views.common import YouPayTransactionCRUD, is_redirect

logger = logging.getLogger(__name__)


class CheckoutpgManager(YouPayTransactionCRUD):

    def __init__(self):
        self.checkoutpg_config = get_checkoutpg_config()
        self.response_obj = YouPayResponse()

    def get_checkout_payment_data(self, data):

        if (data.get('transaction_data') and data.get('request_data')
                and data.get('token_type')):
            payment_data = CheckoutPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data or token_type data "
                "is not available")
            return None

    def get_payment_header(self):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.checkoutpg_config.api_key,
            'Api-key': self.checkoutpg_config.api_key
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
            request_data = data.get('request_data')
            payment_data_to_send = json.dumps(payment_data)
            url = self.checkoutpg_config.domain + CHECKOUTPG_PAYMENT_ENDPOINT
            headers = self.get_payment_header()
            response = requests.post(url, data=payment_data_to_send,
                                     headers=headers)

            if response:
                response_data = response.json()
                logger.info("Checkoutpg payment response: {}"
                            .format(response_data))
                if response_data.get('status') == 200 and response_data.get(
                        'is_redirect') is True:
                    self.update_youpay_transaction_data(
                        {
                            'transaction_id': data.get(
                                'transaction_data').get('transaction_id'),
                            "payment_status": PAYMENT_STATUS_PENDING,
                            "payment_reference": response_data.get(
                                "reference_id"),
                            "payment_gateway": PAYMENT_GATEWAY_CHECKOUTPG,
                            "channel_code": payment_data.get("channel_code"),
                            "payment_method": PAYMENT_METHOD_SAVED_CARD,
                            "card_bin": request_data.get("card_bin"),
                            "card_last4": request_data.get("card_last4"),
                            "payment_scheme": request_data.get(
                                "payment_scheme"),
                            "is_gcc_card": request_data.get("is_gcc_card"),
                            "card_issuer_country": request_data.get(
                                "card_issuer_country"),
                        }
                    )
                return response.json(), self.response_obj.SUCCESS

            return None, self.response_obj.CHECKOUTPG_CONNECTION_ERROR
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.response_obj.CHECKOUTPG_CONNECTION_ERROR

    def card_payemnt(self, data):
        payment_data = self.get_checkout_payment_data(data)
        return payment_data

    def verify_payment(self, data):
        url = self.checkoutpg_config.domain + CHECKOUTPG_PAYMENT_VERIFICATION_ENDPOINT
        transaction_id = data.get('transaction_id')
        youpay_transaction = self.get_youpay_transaction_data(transaction_id)

        params = {
            'cko-session-id': data.get('cko_session_id'),
            'channel_code': youpay_transaction.channel_code,
            'invoice_id': youpay_transaction.invoice_id}
        response = requests.get(url, params=params)

        if response:
            response_data = response.json()
            self.update_youpay_transaction_data(
                {
                    'transaction_id': transaction_id,
                    "payment_status": response_data.get("status").lower(),
                }
            )
            redirect, response_data = is_redirect(transaction_id)
            if redirect:
                return response_data, self.response_obj.SUCCESS
            else:
                return response_data, self.response_obj.PAYMENT_FAILED
        else:
            return None, self.response_obj.CHECKOUTPG_CONNECTION_ERROR
