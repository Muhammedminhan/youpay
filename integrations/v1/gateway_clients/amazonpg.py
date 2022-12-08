import json
import requests
import logging

from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_AMAZONPG, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from core.utils import get_payment_gateway_config
from integrations.constants import (
    AMAZONPG_AUTHENTICATE_API, AMAZONPG_VERIFY_API, AMAZONPG_CACHE_KEY,
    AMAZONPG_HUB_CODE, PAYMENT_REQUEST_VERIFY, AMAZONPG_TOKENIZATION_API
)
from integrations.v1.serializers.amazonpg_payment_request import (
    AmazonPGPaymentRequestSerializer)
from integrations.messages import AMAZONPG_CONNECTION_ERROR_MESSAGE
from payments.constants import (
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_CANCELLED, PAYMENT_METHOD_AMAZON)
from services.v1.views.common import is_redirect

logger = logging.getLogger(__name__)


class AmazonPGManager(PaymentRequestView, PaymentHandlers):
    """
    Class to manage amazonpg related operations
    """
    def __init__(self):
        self.amazonpg_config = get_payment_gateway_config(AMAZONPG_CACHE_KEY,
                                                          AMAZONPG_HUB_CODE)

    def get_amazonpg_payment_data(self, data):
        """
        Returns amazonpg payment request data
        """
        if data.get('transaction_data') and data.get('request_data'):
            payment_data = AmazonPGPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data is not available "
                "for amzonpg")
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
            card_details = data.get('request_data')
            logger.info(
                "Youpay sending card details to amazonpg "
                "is {}".format(card_details))
            payload = card_details

            response = requests.post(url, data=payload)
            logger.info("Response from AmazonPG tokenization api "
                        "{}".format(response))
            if response:
                response_data = response.json()
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
        transaction_id = transaction_data.get('transaction_id')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        is_verified = verify_response.get('is_verified', False)
        """if transaction is verified then proceed with payment"""
        if verify_status == status.HTTP_200_OK and is_verified:
            if self.amazonpg_config:
                payment_data = self.get_amazonpg_payment_data(data)
                logger.info(
                    "Youpay sending payment data to amazonpg "
                    "is {}".format(payment_data))
                payload = json.dumps(payment_data)
                url = self.amazonpg_config.domain + AMAZONPG_AUTHENTICATE_API
                headers = self.get_payment_header()

                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)
                response = requests.post(url, data=payload, headers=headers)
                logger.info("Response from AmazonPG {}".format(response))

                # storing Youpay to payment gateway request and response data
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_id,
                    request_data=payload,
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                )

                if response:
                    response_data = response.json()
                    logger.info("amazonpg payment response: {}"
                                .format(response_data))
                    if (response_data.get('status') == 200 and
                            response_data.get('redirect_url')):
                        update_data = {
                            'transaction_id': transaction_id,
                            "payment_status": PAYMENT_STATUS_PENDING,
                            "payment_gateway": PAYMENT_GATEWAY_AMAZONPG,
                            "channel_code": AMAZONPG_HUB_CODE,
                            "payment_method": PAYMENT_METHOD_AMAZON,
                            "payment_reference": response_data.get(
                                "payment_reference"),
                        }

                        self.update_youpay_transaction_data(update_data)
                    return response_data, self.SUCCESS
                return None, self.AMAZONPG_CONNECTION_ERROR
            else:
                logger.error(AMAZONPG_CONNECTION_ERROR_MESSAGE)
                return None, self.AMAZONPG_CONNECTION_ERROR
        else:
            msg = (
                "Youpay transaction verification failed for transaction id "
                "{} \n response is : {} ".format(transaction_id,
                                                 verify_response))
            logger.error(msg)
            return None, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

    def verify_payment(self, data):
        """
        Method for verifying payment with Amazonpg
        """
        url = self.amazonpg_config.domain + AMAZONPG_VERIFY_API
        transaction_id = data.get('transaction_id')

        params = {
            'payment_reference': data.get('payment_reference'),
        }
        logger.info(
            "Youpay sending payment_reference to amazonpg "
            "is {}".format(params))
        response = requests.get(url, params=params)
        logger.info("Amazonpg verify response: {}".format(response))

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
                return response_data, self.SUCCESS
            else:
                return response_data, self.PAYMENT_FAILED
        else:
            logger.error(
                "Error while verifying_payment amazonpg status: {}, reason "
                "{} \n".format(response.status_code, response.reason))
            return None, self.CHECKOUTPG_CONNECTION_ERROR
