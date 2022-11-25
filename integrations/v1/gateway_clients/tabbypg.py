import json
import logging

import requests
from rest_framework import status

from core.constants import (
    REQUEST_METHOD_POST, PAYMENT_GATEWAY_TABBYPG, REQUEST_METHOD_GET)
from core.utils import get_payment_gateway_config
from integrations.constants import (
    TABBYPG_CREATE_PAYMENT_ENDPOINT,
    PAYMENT_REQUEST_TYPE_PAYMENT, TABBYPG_CACHE_KEY, TABBYPG_HUB_CODE,
    TABBYPG_VERIFY_PAYMENT_ENDPOINT, PAYMENT_REQUEST_VERIFY
)
from integrations.messages import TABBYPG_CONNECTION_ERROR_MESSAGE
from integrations.v1.serializers.tabbypg_payment_request import (
    TabbyPGPaymentRequestSerializer
)
from payments.constants import (
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_CANCELLED, PAYMENT_METHOD_TABBY)
from services.v1.views.common import is_redirect
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class TabbyPGManager(PaymentRequestView, PaymentHandlers):
    def __init__(self):

        self.tabbypg_config = get_payment_gateway_config(TABBYPG_CACHE_KEY,
                                                         TABBYPG_HUB_CODE)
        self.transaction_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_TABBYPG
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None

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
        Step 1 : get transaction id
        Step 2 : get youpaytransaction data corresponding to transaction id
        Step 3 : communicate with tabbypg gateway to create session
        Step 4 : update youpaytransaction
        """

        transaction_data = data.get('transaction_data')

        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_TABBY
        self.payment_status = transaction_data.get('payment_status')
        self.payment_reference = transaction_data.get('payment_reference')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status, verify_response))

        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        try:
            if verify_status == status.HTTP_200_OK and is_verified:

                tabbypg_conf = self.tabbypg_config

                if tabbypg_conf:
                    payment_data = self.get_tabbypg_payment_data(data)
                    logger.info(
                        "Youpay sending payment data is {}".format(
                            payment_data))
                    payment_data_to_send = json.dumps(payment_data)
                    url = (self.tabbypg_config.domain +
                           TABBYPG_CREATE_PAYMENT_ENDPOINT)
                    headers = self.get_payment_header()

                    transaction_obj = self.get_youpay_transaction_data(
                        self.transaction_id)
                    response = requests.post(url, data=payment_data_to_send,
                                             headers=headers)
                    logger.info("TabbyPG response is {}".format(response))
                    response_data = response.json()
                    logger.info("tabbypg payment response: {}"
                                .format(response_data))

                    # storing Youpay to payment gateway request and response data
                    self.create_youpay_to_payment_gateways_data(
                        transaction_obj=transaction_obj,
                        transaction_id=self.transaction_id,
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
                            self.payment_reference = response_data.get(
                                "payment_ref_no")

                            self.payment_status = PAYMENT_STATUS_PENDING
                            return response.json(), self.SUCCESS

                        logger.error("Error in tabbypg payment, {}".format(
                            response.text))

                        self.payment_reference = response_data.get(
                            "payment_ref_no")
                        self.payment_status = response_data.get(
                            "payment_status")

                        return ({"error": response.json()}
                                , self.TABBYPG_CONNECTION_ERROR)

                    return ({"error": response_data},
                            self.TABBYPG_CONNECTION_ERROR)
                else:
                    logger.error(TABBYPG_CONNECTION_ERROR_MESSAGE)
                    return {None}, self.TABBYPG_CONNECTION_ERROR
            else:
                msg = (
                    "Youpay transaction verification failed, transaction id"
                    "{} response is : {} ".format(self.transaction_id,
                                                  verify_response))
                logger.error(msg)
                return None, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            error = "Error in creating session with Tabbypg: {}".format(e)
            logger.error("Exception in tabbypg payment: {}".format(e))
            return {"error": error}, self.TABBYPG_CONNECTION_ERROR
        finally:
            data_to_update = {
                'transaction_id': self.transaction_id,
                "payment_status": self.payment_status,
                "payment_reference": self.payment_reference,
                "payment_gateway": self.payment_gateway,
                "channel_code": self.channel_code,
                "payment_method": self.payment_method,
            }
            self.update_youpay_transaction_data(data_to_update)

    def verify_session(self, data):
        """
        Method for verifying session with Tabbypg
        """
        url = self.tabbypg_config.domain + TABBYPG_VERIFY_PAYMENT_ENDPOINT
        transaction_id = data.get('transaction_id')

        params = {
            'payment_id': data.get('payment_id'),
        }
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
                    "response_summary": response_summary,
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
                "Error while verifying_payment status: {}, reason {}"
                .format(response.status_code, response.reason))
            return None, self.TABBYPG_CONNECTION_ERROR
