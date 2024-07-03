import json
import logging

import requests

from core.constants import REQUEST_METHOD_POST
from core.response_messages import YouPayResponse
from core.utils import get_payment_gateway_config
from integrations.constants import (
    B2CP_CACHE_KEY,
    B2CPAYBACK_HUB_CODE, PAYMENT_REQUEST_COLLECT_POINTS,
    MOKAFA_EARN_POINTS_API, MOKAFA_CLIENT_CODE, )
from payments.constants import PAYMENT_METHOD_MOKAFA

from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class MokafaServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage Mokafa related operations
    """

    def __init__(self):
        self.mokafa_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                        B2CPAYBACK_HUB_CODE)
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.mokafa_config.api_key,
            'X-API-KEY': self.mokafa_config.api_key
        }
        return headers

    def collect_points(self, transaction_obj):
        """
        calls mokafa points collecting api
        """
        try:
            response_obj = YouPayResponse()
            if transaction_obj.earned_point:
                '''if already rewarded'''
                logger.info(
                    "Failed for Reward point, reward already collected "
                    "for ({}), rewarded point {}".format(
                        transaction_obj.transaction_id,
                        transaction_obj.earned_point))
                return None, response_obj.MOKAFA_ALREADY_COLLECTED

            if transaction_obj.payment_method in [
                PAYMENT_METHOD_MOKAFA
            ]:
                paid_amount = transaction_obj.payable_amount
            else:
                paid_amount = transaction_obj.amount

            request_data = {
                "mobile_number": transaction_obj.points_collected_mobile_number,
                "customer_email": transaction_obj.customer_email,
                "customer_name": transaction_obj.customer_name,
                "invoice_id": transaction_obj.invoice_id,
                "gateway_reference": transaction_obj.payment_reference,
                "currency": transaction_obj.currency,
                "client_code": MOKAFA_CLIENT_CODE,
                "amount": str(paid_amount),
                "platform": transaction_obj.platform,

                "item_details_list": transaction_obj.brand_details.get(
                    "item_set", None),
                "brand_calculations": transaction_obj.brand_calculations,
                "language_code": transaction_obj.language,
                "redeemed_amount": (
                    str(transaction_obj.redeemed_amount) if
                    transaction_obj.redeemed_amount else 0),
            }

            self.transaction_obj = transaction_obj
            self.transaction_id = str(self.transaction_obj.transaction_id)

            logger.info(
                "Youpay sending request data to mokafa point collection api "
                "is {}".format(request_data))

            request_data['transaction_id'] = "youpay|" + self.transaction_id
            self.request_data = request_data

            payload = json.dumps(request_data)

            url = self.mokafa_config.domain + MOKAFA_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from mokafa point collection api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                self.response_data = response_data
                logger.info("mokafa point collection api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS
            elif hasattr(response, 'text'):
                self.response_data = json.loads(response.text)
                logger.error("Error in mokafa point collection api, {}"
                             "".format(response.text))
                self.response_data = response.json()
                return {"error": response.text}, self.MOKAFA_CONNECTION_ERROR
            else:
                msg = ("unable to get response from b2c_payback-mokafa for "
                       "point collection")
                logger.error(msg)
                return {"errors": msg}, self.MOKAFA_CONNECTION_ERROR

        except Exception as e:
            logger.error("Exception in mokafa point collection api: "
                         "{}".format(e), exc_info=True)
            return None, self.MOKAFA_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_COLLECT_POINTS,
            )
