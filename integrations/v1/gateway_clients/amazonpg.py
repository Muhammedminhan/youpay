import json
import requests
import logging

from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_AMAZONPG, REQUEST_METHOD_POST)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from core.utils import get_payment_gateway_config
from integrations.constants import (
    AMAZONPG_AUTHENTICATE_API, AMAZONPG_VERIFY_API, AMAZONPG_CACHE_KEY,
    AMAZONPG_HUB_CODE
)
from integrations.v1.serializers.amazonpg_payment_request import (
    AmazonPGPaymentRequestSerializer)
from integrations.messages import AMAZONPG_CONNECTION_ERROR_MESSAGE
from payments.constants import (
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_CANCELLED, PAYMENT_METHOD_AMAZON)

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
