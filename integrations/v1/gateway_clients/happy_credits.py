import json
import requests
import logging

from rest_framework import status

from core.constants import (PAYMENT_GATEWAY_HAPPYCREDITS, REQUEST_METHOD_POST,
                            REQUEST_METHOD_GET)
from integrations.constants import (
    HAPPYCREDITS_HUB_CODE, HAPPYCREDITS_CACHE_KEY, CREDIT_BALANCE_API,
    CREDIT_REDEMPTION_API, CREDIT_REDEMPTION_API,
    PAYMENT_REQUEST_CREDIT_BALANCE)
from integrations.v1.serializers.happy_credits_payment_request import (
    CreditBalanceSerializer)
from integrations.messages import HAPPY_CREDITS_CONNECTION_ERROR_MESSAGE
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from core.utils import get_payment_gateway_config
from payments.constants import PAYMENT_METHOD_CREDIT_BALANCE
from services.v1.views.common import is_redirect

logger = logging.getLogger(__name__)


class HappyCreditsManager(PaymentRequestView, PaymentHandlers):
    """
    Class to manage happy credits related operations
    """

    def __init__(self):
        self.happy_credit_config = get_payment_gateway_config(
            HAPPYCREDITS_CACHE_KEY, HAPPYCREDITS_HUB_CODE)
        self.transaction_id = None
        self.payment_reference = None
        self.credit_balance = None
        self.payment_gateway = PAYMENT_GATEWAY_HAPPYCREDITS
        self.payment_method = PAYMENT_METHOD_CREDIT_BALANCE

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.happy_credit_config.api_key,
            'Api-key': self.happy_credit_config.api_key
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

    def get_credit_balance(self, data):
        """
        Calls happy credits credit balance api.
        """
        try:
            self.transaction_id = (
                data.get('transaction_data').get('transaction_id'))
            if self.happy_credit_config:
                request_data = self.get_credit_balance_request_data(data)
                logger.info("Youpay sending credit balance request data "
                            "to happy credits is {}".format(request_data))
                payload = json.dumps(request_data)
                url = (self.happy_credit_config.domain + CREDIT_BALANCE_API)
                headers = self.get_payment_header()
                transaction_obj = self.get_youpay_transaction_data(
                    self.transaction_id)
                response = requests.post(url, data=payload,
                                         headers=headers)
                logger.info("Response from credit balance api "
                            "{}".format(response))
                # storing Youpay to payment gateway
                # request and response data
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=self.transaction_id,
                    request_data=payload,
                    response_data=response.text,
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_CREDIT_BALANCE
                )
                if response:
                    response_data = response.json()
                    logger.info("Response from credit balance api: {}"
                                .format(response_data))
                    if response_data.get('status') == 200:
                        self.payment_reference = (
                            response_data.get("payment_reference")
                        )
                        self.credit_balance = response_data.get(
                            "credit_balance_in_payment_currency")
                        return response.json(), self.SUCCESS

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
            data_to_update = {
                "transaction_id": self.transaction_id,
                "payment_reference": self.payment_reference,
                "payment_gateway": self.payment_gateway,
                "payment_method": self.payment_method,
                "credit_balance_amount": self.credit_balance
            }
            self.update_youpay_transaction_data(data_to_update)
