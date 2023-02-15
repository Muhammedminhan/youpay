import json
import logging

from core.constants import PAYMENT_GATEWAY_CHECKOUTPG, REQUEST_METHOD_POST
from integrations.constants import (APPLE_PAY_HUB_CODE,
                                    PAYMENT_REQUEST_AUTHENTICATE,
                                    PAYMENT_REQUEST_TYPE_PAYMENT)
from payments.constants import PAYMENT_METHOD_APPLEPAY, \
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_PAID, \
    PAYMENT_STATUS_PENDING
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class ApplePayManager(PaymentRequestView, PaymentHandlers):

    def __init__(self):
        self.transaction_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_CHECKOUTPG
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None
        self.request_data = None
        self.response_data = None
        self.request_type = None
        self.request_method = None
        self.transaction_obj = None

    def initialize_applepay(self, request_data):
        transaction_data = request_data.get('transaction_data')

        self.request_data = request_data.get('request_data')
        self.request_method = REQUEST_METHOD_POST
        self.transaction_id = transaction_data.get(
            'transaction_id')
        self.payment_method = PAYMENT_METHOD_APPLEPAY
        self.channel_code = APPLE_PAY_HUB_CODE
        self.transaction_obj = request_data.get('transaction_obj')

        logger.info("APPLE PAY Validating session {} ".format(
            self.transaction_obj.currency))

        try:
            data_to_update = {
                'transaction_id': self.transaction_id,
                "payment_status": PAYMENT_STATUS_PENDING,
                "payment_gateway": self.payment_gateway,
                "channel_code": self.channel_code,
                "payment_method": self.payment_method,
            }
            self.update_youpay_transaction_data(data_to_update)

            self.response_data = {"message": "success", }
            response_code = self.APPLE_PAY_SUCCESS

            return self.response_data, response_code

        except Exception as e:
            msg = (
                "Error while processing validating session for transaction "
                "id {}, err : {}".format(self.transaction_id, str(e)))
            logger.error(msg)
            return {"error": msg}, self.APPLE_PAY_CONNECTION_ERROR

    def authorize_applepay(self, request_data):
        transaction_data = request_data.get('transaction_data')

        self.request_data = request_data.get('request_data')
        self.request_method = REQUEST_METHOD_POST
        self.transaction_id = transaction_data.get(
            'transaction_id')
        self.payment_method = PAYMENT_METHOD_APPLEPAY
        self.transaction_obj = request_data.get('transaction_obj')

        response_data = request_data.get('response_data')

        logger.info("APPLE PAY Validating session {} ".format(
            self.transaction_obj.currency))

        try:

            self.payment_status = PAYMENT_STATUS_AUTHORIZED

            self.response_data = {
                "message": "success",
                "data": transaction_data
            }
            response_code = self.APPLE_PAY_SUCCESS

            # storing Youpay to payment gateway request and response data
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_AUTHENTICATE,
            )

            return self.response_data, response_code

        except Exception as e:
            msg = (
                "Error while processing applepay autorization for transaction"
                "id {}, err : {}".format(self.transaction_id, str(e)))
            logger.error(msg)
            return {"error": msg}, self.APPLE_PAY_CONNECTION_ERROR
        finally:
            data_to_update = {
                'transaction_id': self.transaction_id,
                "payment_status": self.payment_status,
            }
            self.update_youpay_transaction_data(data_to_update)

    def applepay_payment(self, request_data):
        transaction_data = request_data.get('transaction_data')

        self.request_data = request_data.get('request_data')
        self.request_method = REQUEST_METHOD_POST
        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_APPLEPAY
        self.transaction_obj = request_data.get('transaction_obj')
        response_data = request_data.get('response_data')

        logger.info("APPLE PAY Payment {} ".format(
            self.transaction_obj.currency))

        try:

            # TODO check with FE to get success message format
            self.payment_status = PAYMENT_STATUS_PAID

            self.response_data = {}

            response_code = self.APPLE_PAY_SUCCESS

            # storing Youpay to payment gateway request and response data
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
            )
            return None, response_code

        except Exception as e:
            msg = (
                "Error while processing applepay payment for transaction"
                "id {}, err : {}".format(self.transaction_id, str(e)))
            logger.error(msg)

            return {"error": msg}, self.APPLE_PAY_CONNECTION_ERROR
        finally:
            data_to_update = {
                'transaction_id': self.transaction_id,
                "payment_status": self.payment_status,
            }
            self.update_youpay_transaction_data(data_to_update)
