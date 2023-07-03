import json
import logging

from integrations.constants import PAYMENT_REQUEST_TYPE_NONE
from integrations.models import YoupayToPaymentGatewaysData
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class PaymentHandlers(YouPayTransactionCRUD):
    """To Handle payment requests To/from client"""

    def create_youpay_to_payment_gateways_data(self, **kwargs):
        """method to create the payment request data """
        try:
            payment_request_data = kwargs.get('request_data', None)
            payment_response_data = kwargs.get('response_data', None)

            transaction_id = kwargs.get('transaction_id', None)
            request_type = kwargs.get('request_type',
                                      PAYMENT_REQUEST_TYPE_NONE)
            transaction_obj = kwargs.get('transaction_obj', None)
            request_method = kwargs.get('request_method', None)

            if not transaction_obj:
                """if there is no transaction object passed, then get the 
                data from database"""
                transaction_obj = self.get_youpay_transaction_data(
                    transaction_id)

            # checks weather the transaction object is passed or not
            if transaction_obj:
                create_object = {
                    'payment_request_data': json.loads(
                        json.dumps(json.loads(payment_request_data))),
                    'payment_response_data': json.loads(
                        json.dumps(json.loads(payment_response_data))),
                    'youpay_payment': transaction_obj,
                    'request_type': request_type,
                    'request_method': request_method
                }
                YoupayToPaymentGatewaysData.objects.create(**create_object)
                logger.info("YoupayToPaymentGateways data created for {}"
                            "".format(transaction_obj))
            else:
                logger.error(
                    "YoupayToPaymentGateways failed to save, unable to find "
                    "the transaction object for {}".format(transaction_obj))
        except Exception as e:
            logger.error(
                "YoupayToPaymentGateways data failed to save, {0}".format(
                    str(e)), exc_info=True)
