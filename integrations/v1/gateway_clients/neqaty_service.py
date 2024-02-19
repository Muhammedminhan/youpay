import json
import logging

import requests

from core.constants import (REQUEST_METHOD_POST, PAYMENT_GATEWAY_B2CPAYBACK)
from core.utils import (get_payment_gateway_config)
from integrations.constants import (
    B2CP_CACHE_KEY,
    B2CPAYBACK_HUB_CODE,
    NEQATY_POINT_BALANCE_API, PAYMENT_REQUEST_POINT_BALANCE, )
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class NeqatyServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage Neqaty related operations
    """

    def __init__(self):
        self.neqaty_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                        B2CPAYBACK_HUB_CODE)
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}
        self.request_method = None
        self.request_type = None
        self.payment_status = None
        self.payment_method = None
        self.is_Neqaty_enabled = None
        self.approved = False
        self.amount = None
        self.redeemed_point = None
        self.redeemed_amount = None
        self.redeemed_points = None
        self.payable_amount = None
        self.service_fee = None
        self.base_amount = None
        self.VAT_amount = None
        self.payment_gateway = PAYMENT_GATEWAY_B2CPAYBACK

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.neqaty_config.api_key,
            'X-API-KEY': self.neqaty_config.api_key
        }
        return headers

    def point_balance(self, data):
        """
        calls Neqaty points collecting api
        """
        try:
            request_data = data

            self.transaction_obj = request_data.get('transaction_obj')
            self.transaction_id = str(self.transaction_obj.transaction_id)

            request_data.pop('transaction_obj')

            logger.info(
                "Youpay sending request data to Neqaty point balance api "
                "is {}".format(request_data))

            request_data['transaction_id'] = "youpay|" + self.transaction_id
            self.request_data = request_data

            payload = json.dumps(request_data)

            url = self.neqaty_config.domain + NEQATY_POINT_BALANCE_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from Neqaty point balance api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("Neqaty point balance api response: {}".format(
                    response_data))
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': response_data.get(
                        'payment_reference'),
                })
                return response_data, self.SUCCESS

            logger.error("Error in Neqaty point balance api, {}"
                         "".format(response.text))
            self.response_data = response.json()
            return {"error": response.text}, self.NEQATY_CONNECTION_ERROR

        except Exception as e:
            error = "Error in Neqaty point balance api: {}".format(e)
            logger.error("Exception in Neqaty point balance api: "
                         "{}".format(e), exc_info=True)
            return {"error": error}, self.NEQATY_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_POINT_BALANCE,
            )
