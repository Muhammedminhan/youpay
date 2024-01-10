import json
import logging

import requests
from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_AMAZONPG, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from core.utils import get_payment_gateway_config
from integrations.constants import (
    AMAZONPG_AUTHENTICATE_API, AMAZONPG_VERIFY_API, AMAZONPG_CACHE_KEY,
    AMAZONPG_HUB_CODE, PAYMENT_REQUEST_VERIFY, AMAZONPG_TOKENIZATION_API,
    AMAZONPG_REFUND_API, PAYMENT_REQUEST_AUTHENTICATE, PAYMENT_REQUEST_REFUND
)
from integrations.messages import AMAZONPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.amazonpg_payment_request import (
    AmazonPGCardPaymentRequestSerializer, AmazonPGTokenizationSerializer,
    AmazonPGApplepayPaymentRequestSerializer)
from payments.constants import (
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_CANCELLED, PAYMENT_METHOD_AMAZON,
    PAYMENT_STATUS_REFUNDED, PAYMENT_METHOD_CARD, PAYMENT_METHOD_APPLEPAY)
from services.v1.views.common import is_redirect
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class AmazonPGManager(PaymentRequestView, PaymentHandlers):
    """
    Class to manage amazonpg related operations
    """
    def __init__(self):
        self.amazonpg_config = get_payment_gateway_config(AMAZONPG_CACHE_KEY,
                                                          AMAZONPG_HUB_CODE)
        self.transaction_id = None
        self.payment_method = PAYMENT_METHOD_AMAZON
        self.payment_gateway = PAYMENT_GATEWAY_AMAZONPG
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None
        self.request_data = None
        self.response_data = None
        self.request_type = None
        self.request_method = None
        self.transaction_obj = None
        self.payment_scheme = None
        self.name_on_card = None

    def prepare_data_to_update(self):
        data_to_update = {
            'transaction_id': self.transaction_id,
            "payment_status": self.payment_status,
            "payment_reference": self.payment_reference,
            "payment_gateway": self.payment_gateway,
            "channel_code": self.channel_code,
            "payment_method": self.payment_method,
            "payment_scheme": self.payment_scheme,
            "name_on_card": self.name_on_card
        }
        return data_to_update

    def get_amazonpg_card_payment_data(self, data):
        """
        Returns amazonpg card payment request data
        """
        if data.get('transaction_data') and data.get('request_data'):
            payment_data = AmazonPGCardPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data is not available "
                "for amzonpg")
            return None

    def get_amazonpg_applepay_payment_data(self, data):
        """
        Returns amazonpg applepay payment request data
        """
        if data.get('transaction_data') and data.get('request_data'):
            payment_data = AmazonPGApplepayPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data is not available "
                "for amzonpg")
            return None

    def get_amazon_payment_data(self, payment_method, data):
        payment_data = {}
        if payment_method == PAYMENT_METHOD_CARD:
            payment_data = self.get_amazonpg_card_payment_data(
                data)

        elif payment_method == PAYMENT_METHOD_APPLEPAY:
            payment_data = self.get_amazonpg_applepay_payment_data(
                data)

        return payment_data

    def get_tokenization_data(self, data):
        """
        Returns amazonpg tokenization api request data
        """
        if data.get('transaction_data') and data.get('request_data'):
            tokenization_data = AmazonPGTokenizationSerializer(data)
            return tokenization_data.data
        else:
            logger.error(
                "transaction_data or request_data is not available "
                "for amzonpg tokenization")
            return None

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.amazonpg_config.api_key,
            'HTTP-X-API-KEY': self.amazonpg_config.api_key
        }
        return headers

    def tokenization(self, data):
        """
        Calls amazonpg tokenization api
        """
        try:

            url = self.amazonpg_config.domain + AMAZONPG_TOKENIZATION_API
            card_details = self.get_tokenization_data(data)
            logger.info(
                "Youpay sending card details to amazonpg "
                "is {}".format(card_details))
            payload = card_details

            response = requests.post(url, data=payload)
            if response:
                response_data = response.json()
                logger.info("Response from AmazonPG tokenization api "
                            "{}".format(response_data))
                return response_data, self.SUCCESS
        except Exception as e:
            error = "Error in amazonpg tokenization api: {}".format(e)
            logger.error("Exception in amazonpg payment: {}".format(e))
            return {"error": error}, self.AMAZONPG_CONNECTION_ERROR

    def payment_authentication(self, data):
        """
        Calls amazonpg authentication api
        """
        transaction_data = data.get('transaction_data')
        request_data = data.get('request_data')
        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_status = transaction_data.get('payment_status')
        self.payment_reference = transaction_data.get('payment_reference')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        try:
            if verify_status == status.HTTP_200_OK and is_verified:
                if self.amazonpg_config:
                    payment_method = PAYMENT_METHOD_APPLEPAY
                    payment_data = self.get_amazon_payment_data(
                        payment_method, request_data)

                    logger.info(
                        "Youpay sending payment data to amazonpg "
                        "is {}".format(payment_data))
                    payload = json.dumps(payment_data)
                    url = (self.amazonpg_config.domain +
                           AMAZONPG_AUTHENTICATE_API)
                    headers = self.get_payment_header()

                    transaction_obj = self.get_youpay_transaction_data(
                        self.transaction_id)
                    response = requests.post(url, data=payload,
                                             headers=headers)
                    logger.info("Response from AmazonPG {}".format(response))

                    # storing Youpay to payment gateway
                    # request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=self.transaction_id,
                        request_data=payload,
                        response_data=response.text,
                        request_method=REQUEST_METHOD_POST,
                        request_type=PAYMENT_REQUEST_AUTHENTICATE
                    )

                    if response:
                        response_data = response.json()
                        logger.info("amazonpg payment response: {}"
                                    .format(response_data))
                        if (response_data.get('status') == 200 and
                                response_data.get('redirect_url')):
                            self.payment_reference = response_data.get(
                                "payment_reference")
                            self.payment_status = PAYMENT_STATUS_PENDING
                            self.payment_scheme = response_data.get(
                                "payment_scheme")
                            self.name_on_card = response_data.get(
                                "name_on_card")

                            self.update_youpay_transaction_data(
                                self.prepare_data_to_update())
                            return response.json(), self.SUCCESS

                        logger.error("Error in amazonpg payment, {}".format(
                            response.text))
                        self.payment_reference = response_data.get(
                            "payment_reference")

                        self.update_youpay_transaction_data(
                            self.prepare_data_to_update())
                        return ({"error": response.json()},
                                self.AMAZONPG_CONNECTION_ERROR)

                    return ({"error": response.text},
                            self.AMAZONPG_CONNECTION_ERROR)
                else:
                    logger.error(AMAZONPG_CONNECTION_ERROR_MESSAGE)
                    return {None}, self.AMAZONPG_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay transaction verification failed "
                    "for transaction id {} response is : "
                    "{} ".format(self.transaction_id, verify_response))
                logger.error(msg)
                return verify_response, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            error = "Error in amazonpg authentication api: {}".format(e)
            logger.error("Exception in amazonpg payment: {}".format(e))
            return {"error": error}, self.AMAZONPG_CONNECTION_ERROR

    def verify_payment(self, data):
        """
        Method for verifying payment with Amazonpg
        """
        url = self.amazonpg_config.domain + AMAZONPG_VERIFY_API
        transaction_id = data.get('transaction_id')

        params = {
            'payment_reference': data.get('payment_reference'),
        }

        self.transaction_obj = self.get_youpay_transaction_data(
            transaction_id)
        self.transaction_id = transaction_id
        self.request_data = json.dumps(params)
        self.request_type = PAYMENT_REQUEST_VERIFY
        self.request_method = REQUEST_METHOD_GET

        if self.transaction_obj is None:
            return None, self.TRANSACTION_NOT_FOUND

        try:
            # if transaction is already verified then redirect to
            # corresponding client url
            if self.transaction_obj.payment_status == PAYMENT_STATUS_PAID:
                response_data = {
                    "is_redirect": True,
                    "redirect_url": (self.transaction_obj.success_url +
                                     '?transaction_id=' + transaction_id),
                    "transaction_message": {
                        "status": 200,
                        "is_capture": True,
                        "message": "Duplicate verification"
                    }
                }
                self.response_data = json.dumps(response_data)

                return response_data, self.SUCCESS

            response = requests.get(url, params=params)
            logger.info("Amazonpg verify response: {}".format(response))

            if response:
                response_data = response.json()
                logger.info(
                    "Verify payment response data {}".format(response_data))

                if response_data.get('is_capture'):
                    payment_status = PAYMENT_STATUS_PAID
                    approved = True
                    response_summary = "Payment successful"
                else:
                    payment_status = PAYMENT_STATUS_CANCELLED
                    approved = False
                    response_summary = "Payment failed"

                self.update_youpay_transaction_data(
                    {
                        'transaction_id': transaction_id,
                        "payment_status": payment_status,
                        "approved": approved,
                        "response_summary": response_summary
                    }
                )

                redirect, response_data = is_redirect(transaction_id,
                                                      response_data)
                if redirect:
                    self.response_data = json.dumps(response_data)
                    return response_data, self.SUCCESS
                else:
                    self.response_data = json.dumps(response_data)
                    return response_data, self.PAYMENT_FAILED
            else:
                logger.error("Error while verifying_payment amazonpg "
                             "status: {}, reason {} "
                             "".format(response.status_code, response.text))
                return None, self.AMAZONPG_CONNECTION_ERROR
        except Exception as e:
            logger.error("Exception in amazonpg verify session: {}"
                         "".format(str(e)))
            return {"error": e}, self.AMAZONPG_CONNECTION_ERROR
        finally:
            # storing Youpay to payment gateway request and response data
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=self.request_data,
                response_data=self.response_data,
                request_type=self.request_type,
                request_method=self.request_method,
            )

    def payment_refund(self, data):
        """
        Method for refund the payment with Amazonpg
        """
        url = self.amazonpg_config.domain + AMAZONPG_REFUND_API

        payload = {
            'payment_reference': data.get('payment_reference'),
        }

        self.transaction_obj = data.get('transaction_obj')

        if not self.transaction_obj:
            return None, self.TRANSACTION_NOT_FOUND

        self.transaction_id = self.transaction_obj.transaction_id
        self.request_data = json.dumps(payload)
        self.request_type = PAYMENT_REQUEST_REFUND
        self.request_method = REQUEST_METHOD_POST
        try:
            response = requests.post(url, data=payload)
            logger.info("Response from AmazonPG refund api "
                        "{}".format(response))
            if response:
                response_data = response.json()
                logger.info(
                    "Refund payment response data {}".format(response_data))
                if response_data.get('is_refund'):
                    payment_status = PAYMENT_STATUS_REFUNDED
                    response_summary = "Refund successful"
                else:
                    payment_status = PAYMENT_STATUS_CANCELLED
                    response_summary = "Refund failed"

                self.update_youpay_transaction_data(
                    {
                        'transaction_id': self.transaction_id,
                        "payment_status": payment_status,
                        "response_summary": response_summary
                    }
                )

                if payment_status == PAYMENT_STATUS_REFUNDED:
                    return payment_status, self.SUCCESS
                else:
                    return payment_status, self.PAYMENT_FAILED
            else:
                logger.error("Error while refund_payment amazonpg "
                             "status: {}, reason {} "
                             "".format(response.status_code, response.text))
                return None, self.AMAZONPG_CONNECTION_ERROR
        except Exception as e:
            logger.error("Exception in amazonpg refund api call: {}"
                         "".format(str(e)))
            return {"error": e}, self.AMAZONPG_CONNECTION_ERROR
