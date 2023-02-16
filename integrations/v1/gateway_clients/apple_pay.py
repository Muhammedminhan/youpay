import logging

from core.constants import PAYMENT_GATEWAY_CHECKOUTPG
from payments.constants import (PAYMENT_METHOD_APPLEPAY, \
                                PAYMENT_STATUS_AUTHORIZED,
                                PAYMENT_STATUS_NONE, PAYMENT_STATUS_PAID, \
                                PAYMENT_STATUS_PENDING)
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
        self.response_data = {}
        self.request_type = None
        self.request_method = None
        self.transaction_obj = None

    def update_status(self, request_data):
        transaction_data = request_data.get('transaction_data')
        self.request_data = request_data.get('request_data')
        self.transaction_id = transaction_data.get('transaction_id')
        self.payment_method = PAYMENT_METHOD_APPLEPAY
        self.transaction_obj = request_data.get('transaction_obj')

        # status may be pending, authorized, paid
        payment_stage = request_data.get('payment_stage')

        logger.info("APPLE PAY Status update for {} to {} ".format(
            self.transaction_id, payment_stage))

        try:

            response_code = self.APPLE_PAY_SUCCESS

            if payment_stage == PAYMENT_STATUS_PENDING:
                self.payment_status = PAYMENT_STATUS_PENDING
                message = "Apple pay payment updated to pending"

            elif payment_stage == PAYMENT_STATUS_AUTHORIZED:
                self.payment_status = PAYMENT_STATUS_AUTHORIZED
                message = "Apple pay payment updated to authorized"
                self.response_data["data"] = transaction_data

            elif payment_stage == PAYMENT_STATUS_PAID:
                self.payment_status = PAYMENT_STATUS_PAID
                message = "Apple pay payment updated to paid"
                redirect_url = (transaction_data['success_url'] +
                        '?transaction_id=' + transaction_data['transaction_id'])
                
                self.response_data['redirect_url'] = redirect_url
                self.response_data['is_redirect'] = True

            else:
                message = (
                    "APPLE PAY Invalid payment stage received {} for"
                    " transaction id {}, status {}".format(
                        payment_stage,
                        self.transaction_id,
                        self.payment_status))

                self.payment_status = PAYMENT_STATUS_NONE
                response_code = self.APPLE_PAY_BAD_REQUEST

            logger.info(message)
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
