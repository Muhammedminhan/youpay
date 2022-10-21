import json
import logging

import requests
from django.conf import settings
from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_CHECKOUTPG, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from core.utils import get_checkoutpg_config
from integrations.constants import (CHECKOUTPG_PAYMENT_CONFIGURATIONS,
                                    CHECKOUTPG_CONFIG_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT_V2,
                                    CHECKOUTPG_SAVED_CARD_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_ENDPOINT,
                                    CHECKOUTPG_PAYMENT_VERIFICATION_ENDPOINT)
from integrations.constants import (
    PAYMENT_REQUEST_TYPE_CARD,
    PAYMENT_REQUEST_TYPE_SAVED_CARD,
    PAYMENT_REQUEST_VERIFY, )
from integrations.messages import CHECKOUTPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.checkoutpg_payment_request import (
    CheckoutPaymentRequestSerializer)
from payments.constants import (PAYMENT_STATUS_PENDING,
                                PAYMENT_METHOD_SAVED_CARD,
                                PAYMENT_METHOD_CARD)
from services.v1.views.common import (is_redirect)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class CheckoutpgManager(PaymentRequestView, PaymentHandlers):

    def __init__(self):
        self.checkoutpg_config = get_checkoutpg_config()

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

    def get_configurations(self, currency):
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
                        return data, self.SUCCESS

                    return message, resp_status
                logger.error("Unable to fetch Checkoutpg configurations.")
                return None, self.CHECKOUTPG_CONNECTION_ERROR
            except Exception as e:
                logger.error(
                    "Failed to fetch the checkoutpg v2 configuration "
                    "data {}".format(e))
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        else:
            logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
            return None, self.CHECKOUTPG_CONNECTION_ERROR

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
                    return saved_cards

            except Exception as e:
                logger.error(
                    "Unable to fetch saved card details for user {0} "
                    "because, {1}".format(email, str(e)))
                return None
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

        transaction_data = data.get('transaction_data')
        transaction_id = transaction_data.get('transaction_id')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status, verify_response))

        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        if verify_status == status.HTTP_200_OK and is_verified:

            checkoutpg_config = get_checkoutpg_config()

            if checkoutpg_config:
                success_dict = {}
                payment_data = self.get_checkout_payment_data(data)
                logger.info(
                    "Youpay sending payment data is {}".format(payment_data))
                request_data = data.get('request_data')
                payment_data_to_send = json.dumps(payment_data)
                url = self.checkoutpg_config.domain + CHECKOUTPG_PAYMENT_ENDPOINT
                headers = self.get_payment_header()

                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                response = requests.post(url, data=payment_data_to_send,
                                         headers=headers)

                # storing Youpay to payment gateway request and response data
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_id,
                    request_data=payment_data_to_send,
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_SAVED_CARD,
                )

                if response:
                    response_data = response.json()
                    logger.info("Checkoutpg payment response: {}"
                                .format(response_data))
                    if response_data.get(
                            'status') == 200 and response_data.get(
                        'is_redirect') is True:
                        self.update_youpay_transaction_data(
                            {
                                'transaction_id': data.get(
                                    'transaction_data').get('transaction_id'),
                                "payment_status": PAYMENT_STATUS_PENDING,
                                "payment_reference": response_data.get(
                                    "reference_id"),
                                "payment_gateway": PAYMENT_GATEWAY_CHECKOUTPG,
                                "channel_code": payment_data.get(
                                    "channel_code"),
                                "payment_method": PAYMENT_METHOD_SAVED_CARD,
                            }
                        )
                    return response.json(), self.SUCCESS

                return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        else:
            msg = (
                "Youpay transaction verification failed for transaction id "
                "{} \n response is : {} ".format(transaction_id,
                                                 verify_response))
            logger.error(msg)
            return None, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

    def card_payment(self, data):
        transaction_data = data.get('transaction_data')
        transaction_id = transaction_data.get('transaction_id')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)

        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        if verify_status == status.HTTP_200_OK and is_verified:
            checkoutpg_config = get_checkoutpg_config()
            if checkoutpg_config:
                success_dict = {}
                payment_data = self.get_checkout_payment_data(data)
                logger.info(
                    "Youpay sending payment data is {}".format(payment_data))
                request_data = data.get('request_data')
                payment_data_to_send = json.dumps(payment_data)
                url = self.checkoutpg_config.domain + CHECKOUTPG_PAYMENT_ENDPOINT
                headers = self.get_payment_header()

                transaction_id = data.get('transaction_data').get(
                    'transaction_id')
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                response = requests.post(url, data=payment_data_to_send,
                                         headers=headers)
                # storing Youpay to payment gateway request and response data
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=data.get('transaction_data').get(
                        'transaction_id'),
                    request_data=payment_data_to_send,
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_CARD,
                )

                if response:
                    response_data = response.json()
                    logger.info("Checkoutpg payment response: {}"
                                .format(response_data))
                    if response_data.get(
                            'status') == 200 and response_data.get(
                        'is_redirect') is True:
                        self.update_youpay_transaction_data(
                            {
                                'transaction_id': data.get(
                                    'transaction_data').get('transaction_id'),
                                "payment_status": PAYMENT_STATUS_PENDING,
                                "payment_reference": response_data.get(
                                    "reference_id"),
                                "payment_gateway": PAYMENT_GATEWAY_CHECKOUTPG,
                                "channel_code": payment_data.get(
                                    "channel_code"),
                                "payment_method": PAYMENT_METHOD_CARD,
                            }
                        )
                    return response.json(), self.SUCCESS
                return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                logger.error(CHECKOUTPG_CONNECTION_ERROR_MESSAGE)
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        else:
            msg = (
                "Youpay transaction verification failed for transaction id "
                "{} \n response is : {} ".format(transaction_id,
                                                 verify_response))
            logger.error(msg)
            return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

    def verify_payment(self, data):
        url = self.checkoutpg_config.domain + CHECKOUTPG_PAYMENT_VERIFICATION_ENDPOINT
        transaction_id = data.get('transaction_id')
        youpay_transaction = self.get_youpay_transaction_data(transaction_id)

        params = {
            'cko-session-id': data.get('cko_session_id'),
            'channel_code': youpay_transaction.channel_code,
            'invoice_id': youpay_transaction.invoice_id}
        response = requests.get(url, params=params)

        transaction_obj = self.get_youpay_transaction_data(transaction_id)

        # storing Youpay to payment gateway request and response data
        self.create_youpay_to_payment_gateways_data(
            transaction_obj=transaction_obj,
            transaction_id=transaction_id,
            request_data=json.dumps(params),
            response_data=response.text,
            request_type=PAYMENT_REQUEST_VERIFY,
            request_method=REQUEST_METHOD_GET,
        )

        if response:
            response_data = response.json()
            logger.info(
                "Verify payment response data \n{}".format(response_data))
            self.update_youpay_transaction_data(
                {
                    'transaction_id': transaction_id,
                    "payment_status": response_data.get("status").lower(),
                    "payment_reference": response_data.get("reference"),
                    "approved": response_data.get("approved"),
                    "response_summary": response_data.get("response_summary"),
                }
            )
            redirect, response_data = is_redirect(transaction_id,
                                                  response_data)
            if redirect:
                return response_data, self.SUCCESS
            else:
                return response_data, self.PAYMENT_FAILED
        else:
            logger.error(
                "Error while verifying_payment status: {}, reason {} \n"
                .format(response.status_code, response.reason))
            return None, self.CHECKOUTPG_CONNECTION_ERROR
