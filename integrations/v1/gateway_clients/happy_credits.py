import json
import requests
import logging

from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_HAPPYCREDITS, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from integrations.constants import (
    HAPPYCREDITS_HUB_CODE, HAPPYCREDITS_CACHE_KEY, CREDIT_BALANCE_API,
    CREDIT_REDEMPTION_API, PAYMENT_REQUEST_CREDIT_BALANCE,
    PAYMENT_REQUEST_REDEMPTION)
from integrations.v1.serializers.happy_credits_payment_request import (
    CreditBalanceSerializer)
from integrations.v1.gateway_clients.utils import get_credit_redemption_data
from integrations.messages import HAPPY_CREDITS_CONNECTION_ERROR_MESSAGE
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from core.utils import (get_payment_gateway_config, decrypt_string,
                        decrypt_payment_data)
from payments.constants import (PAYMENT_METHOD_CREDIT_BALANCE,
                                PAYMENT_STATUS_PAID, PAYMENT_STATUS_CANCELLED)
from services.v1.views.common import is_redirect

logger = logging.getLogger(__name__)


class HappyCreditsManagement(PaymentRequestView, PaymentHandlers):
    """
    Class to manage happy credits related operations
    """

    def __init__(self):
        self.happy_credit_config = get_payment_gateway_config(
            HAPPYCREDITS_CACHE_KEY, HAPPYCREDITS_HUB_CODE)
        self.transaction_id = None
        self.credit_balance = None
        self.transaction_obj = None
        self.payment_reference = None
        self.gateway_request_data = None
        self.gateway_response_data = None

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.happy_credit_config.api_key,
            'X-API-KEY': self.happy_credit_config.api_key
        }
        return headers

    def get_credit_balance_request_data(self, data):
        """
        Returns happy credits balance request data
        """
        if data.get('transaction_data'):
            balance_request_data = CreditBalanceSerializer(data)
            return balance_request_data.data
        else:
            logger.error("transaction_data is not "
                         "available for happy credits")
            return None

    def update_payment_gateway(self, request_type):
        """
        storing Youpay to payment gateway request and response data
        """
        self.create_youpay_to_payment_gateways_data(
            transaction_obj=self.transaction_obj,
            transaction_id=self.transaction_id,
            request_data=json.dumps(self.gateway_request_data),
            response_data=json.dumps(self.gateway_response_data),
            request_type=request_type,
            request_method=REQUEST_METHOD_POST,
        )

    def update_transaction_data(self, request_type, response_data=None):
        """
        Update youpay transaction data based on response
        """

        if request_type == PAYMENT_REQUEST_REDEMPTION:
            if response_data.get('is_capture'):
                payment_status = PAYMENT_STATUS_PAID
                approved = True
                response_summary = "Payment successful"
                available_balance = response_data.get(
                    'available_balance_in_payment_currency')
            else:
                payment_status = PAYMENT_STATUS_CANCELLED
                approved = False
                response_summary = "Payment failed"
                available_balance = None
            data_to_update = {
                'transaction_id': self.transaction_id,
                "payment_status": payment_status,
                "approved": approved,
                "response_summary": response_summary,
                "available_credit_balance": available_balance
            }
        else:
            data_to_update = {
                "transaction_id": self.transaction_id,
                "payment_reference": self.payment_reference,
                "payment_gateway": PAYMENT_GATEWAY_HAPPYCREDITS,
                "payment_method": PAYMENT_METHOD_CREDIT_BALANCE,
                "credit_balance_amount": self.credit_balance
            }
        self.update_youpay_transaction_data(data_to_update)

    def get_credit_balance(self, data):
        """
        Calls happy credits credit balance api.
        """
        try:
            self.transaction_id = (
                data.get('transaction_data').get('transaction_id'))
            if self.happy_credit_config:
                request_data = self.get_credit_balance_request_data(data)
                self.gateway_request_data = request_data
                request_data = json.dumps(request_data)
                logger.info("Youpay sending credit balance request data "
                            "to happy credits is {}".format(request_data))
                url = (self.happy_credit_config.domain + CREDIT_BALANCE_API)
                headers = self.get_payment_header()
                self.transaction_obj = self.get_youpay_transaction_data(
                    self.transaction_id)
                response = requests.post(url, data=request_data,
                                         headers=headers)
                logger.info("Response from credit balance api "
                            "{}".format(response))

                if response:
                    response_decrypted = response.json()
                    response_data = decrypt_payment_data(response_decrypted)
                    self.gateway_response_data = response_data
                    logger.info("Response from credit balance api: {}"
                                .format(response_data))
                    if response_data.get('status') == 200:
                        self.payment_reference = (
                            response_data.get("payment_reference")
                        )
                        self.credit_balance = response_data.get(
                            "credit_balance_in_payment_currency")
                        return response_data, self.SUCCESS

                    logger.error("Error in credit balance api, {}".format(
                        response.text))
                    self.payment_reference = response_data.get(
                        "payment_reference")
                    return ({"error": response_data},
                            self.HAPPY_CREDITS_CONNECTION_ERROR)

                return ({"error": response.text},
                        self.HAPPY_CREDITS_CONNECTION_ERROR)
            else:
                logger.error(HAPPY_CREDITS_CONNECTION_ERROR_MESSAGE)
                return {None}, self.HAPPY_CREDITS_CONNECTION_ERROR

        except Exception as e:
            error = "Error in happy credits credit balance api: {}".format(e)
            logger.error("Exception in happy credits credit "
                         "balance api: {}".format(e))
            return {"error": error}, self.HAPPY_CREDITS_CONNECTION_ERROR

        finally:
            self.update_transaction_data(PAYMENT_REQUEST_CREDIT_BALANCE)
            self.update_payment_gateway(PAYMENT_REQUEST_CREDIT_BALANCE)

    def debit_balance(self, data):
        """
        Calls happy credits deduct balance api.
        """
        try:
            self.transaction_id = decrypt_string(data.get('transaction_id'))
            self.transaction_obj = self.get_youpay_transaction_data(
                self.transaction_id)
            request_data = get_credit_redemption_data(data,
                                                      self.transaction_obj)
            self.gateway_request_data = request_data
            request_data = json.dumps(request_data)
            logger.info("Youpay sending credit redemption request data "
                        "to happy credits is {}".format(request_data))
            if self.transaction_obj is None:
                return None, self.TRANSACTION_NOT_FOUND

            url = (self.happy_credit_config.domain + CREDIT_REDEMPTION_API)
            headers = self.get_payment_header()
            response = requests.post(url, data=request_data,
                                     headers=headers)
            logger.info("Response from credit redemption api "
                        "{}".format(response))
            if response:
                response_decrypted = response.json()
                response_data = decrypt_payment_data(response_decrypted)
                logger.info(
                    "Balance deduct response data {}".format(response_data))
                self.update_transaction_data(PAYMENT_REQUEST_REDEMPTION,
                                             response_data)

                redirect, response_data = is_redirect(self.transaction_id,
                                                      response_data)
                self.gateway_response_data = response_data
                if redirect:
                    return response_data, self.SUCCESS
                else:
                    return response_data, self.PAYMENT_FAILED
            else:
                logger.error("Error while deducting balance from happycredits"
                             " status: {}, reason {} "
                             "".format(response.status_code, response.text))
                return None, self.HAPPY_CREDITS_CONNECTION_ERROR
        except Exception as e:
            logger.error("Exception in happy credits deduct balance session:"
                         " {}".format(str(e)))
            return {"error": e}, self.HAPPY_CREDITS_CONNECTION_ERROR
        finally:
            self.update_payment_gateway(PAYMENT_REQUEST_REDEMPTION)
