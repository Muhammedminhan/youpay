import json
import logging

import requests
from rest_framework import status

from core.constants import REQUEST_METHOD_POST, PAYMENT_GATEWAY_TABBYPG
from core.utils import get_tabbypg_config
from integrations.constants import TABBYPG_CREATE_PAYMENT_ENDPOINT, \
    PAYMENT_REQUEST_TYPE_PAYMENT
from integrations.messages import TABBYPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.tabbypg_payment_request import \
    TabbyPGPaymentRequestSerializer
from payments.constants import PAYMENT_STATUS_PENDING
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class TabbyPGManager(PaymentRequestView, PaymentHandlers):
    def __init__(self):
        self.tabbypg_config = get_tabbypg_config()

    def get_tabbypg_payment_data(self, data):

        if (data.get('transaction_data') and data.get('request_data')):
            payment_data = TabbyPGPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data data is not available")
            return None

    def get_payment_header(self):
        logger.info("get_payment_header using ?")
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.tabbypg_config.api_key,
            'Api-key': self.tabbypg_config.api_key
        }
        return headers

    def create_session(self, data):
        """
        Method for creating session with Tabbypg
        Sample data input : TABBY_CREATE_SESSION_SAMPLE_BODY
        Step 1 : get transaction id
        Step 2 : get youpaytransaction data corresponding to transaction id
        Step 3 : communicate with tabbypg gateway to create session
        Step 4 : update youpaytransaction
        """

        transaction_data = data.get('transaction_data')
        transaction_id = transaction_data.get('transaction_id')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status, verify_response))

        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        if verify_status == status.HTTP_200_OK and is_verified:

            tabbypg_conf = self.tabbypg_config

            if tabbypg_conf:
                success_dict = {}
                payment_data = self.get_tabbypg_payment_data(data)
                logger.info(
                    "Youpay sending payment data is {}".format(payment_data))
                request_data = data.get('request_data')
                payment_data_to_send = json.dumps(payment_data)
                url = self.tabbypg_config.domain + TABBYPG_CREATE_PAYMENT_ENDPOINT
                headers = self.get_payment_header()

                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

                response = requests.post(url, data=payment_data_to_send,
                                         headers=headers)
                logger.info("TabbyPG response is {}".format(response))
                response_data = response.json()
                logger.info("tabbypg payment response: {}"
                            .format(response_data))

                # storing Youpay to payment gateway request and response data
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=transaction_id,
                    request_data=payment_data_to_send,
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
                )

                if response:
                    response_data = response.json()
                    logger.info("tabbypg payment response: {}"
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
                                "payment_gateway": PAYMENT_GATEWAY_TABBYPG,
                                "channel_code": payment_data.get(
                                    "channel_code"),
                                "payment_method": "",
                            }
                        )
                    return response.json(), self.SUCCESS

                return None, self.CHECKOUTPG_CONNECTION_ERROR
            else:
                logger.error(TABBYPG_CONNECTION_ERROR_MESSAGE)
                return None, self.CHECKOUTPG_CONNECTION_ERROR
        else:
            msg = (
                "Youpay transaction verification failed for transaction id "
                "{} \n response is : {} ".format(transaction_id,
                                                 verify_response))
            logger.error(msg)
            return None, self.CLIENT_TRANSACTION_VERIFICATION_FAILED

    def verify_session(self, data):
        """
        Method for verifying session with Tabbypg
        """

        pass
