import json
import logging

import requests

from core.constants import REQUEST_METHOD_POST
from core.utils import get_payment_gateway_config
from integrations.constants import (
    QITAF_OTP_GENERATION_API, QITAF_EARN_POINTS_API, QITAF_REDEEM_POINTS_API,
    QITAF_REVERSE_POINTS_API, QITAF_REWARD_UPDATE_API, B2CP_CACHE_KEY,
    B2CPAYBACK_HUB_CODE, PAYMENT_REQUEST_TYPE_PAYMENT,
    PAYMENT_REQUEST_REDEMPTION
)
from integrations.v1.serializers.qitafpg_serializer import (
    QitafPaymentRequestSerializer
)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class QitafServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage qitaf related operations
    """

    def __init__(self):
        self.qitaf_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                       B2CPAYBACK_HUB_CODE)
        self.transaction_id = None
        self.transaction_obj = None
        self.request_data = {}
        self.response_data = {}
        self.request_method = None
        self.request_type = None

    def get_qitaf_payment_data(self, data):
        if data.get('transaction_obj'):
            payment_data = QitafPaymentRequestSerializer(data)
            return payment_data.data
        else:
            logger.error(
                "transaction_data or request_data or token_type data "
                "is not available")
            return None

    def update_qitaf_phone_number(self, data):
        """
        To update qitaf phone number
        """
        try:
            return self.update_youpay_transaction_data(data)
        except Exception as e:
            error = "Exception in update_qitaf_phone_number: {}".format(e)
            logger.error(error)
            return False

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.qitaf_config.api_key,
            'X-API-KEY': self.qitaf_config.api_key
        }
        return headers

    def generate_otp(self, data):
        """
        calls qitaf otp generating api and returns otp
        """
        try:
            request_data = data['request_data']
            self.transaction_obj = request_data.get('transaction_obj')
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.get_qitaf_payment_data(request_data)

            data = {
                'transaction_id': str(self.transaction_id),
                'qitaf_phone_number': request_data.get("mobile_number"),
                'is_qitaf_enabled': str(True)
            }

            self.update_qitaf_phone_number(data)

            payload.update(data)
            self.request_data = payload
            payload['MSISDN'] = payload['qitaf_phone_number']
            logger.info(
                "Youpay sending request data to qitaf generate otp api "
                "is {}".format(payload))
            url = self.qitaf_config.domain + QITAF_OTP_GENERATION_API
            headers = self.get_payment_header()

            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            logger.info("Response from Qitaf service {}".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf payment response: {}".format(
                    response_data))
                self.response_data = response_data
                self.update_youpay_transaction_data({
                    'transaction_id': self.transaction_obj.transaction_id,
                    'payment_reference': response_data.get(
                        'payment_reference'),
                })

                return response_data, self.SUCCESS

            logger.error("Error in qitaf otp, {}".format(response.json()))
            self.response_data = response.json()

            return ({"error": response.json()},
                    self.QITAF_CONNECTION_ERROR)

        except Exception as e:
            error = "Exception in qitaf generate otp api: {}".format(e)
            logger.error(error, exc_info=True)
            self.response_data = {}
            return {"error": error}, self.QITAF_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
            )

    def collect_points(self, data):
        """
        calls qitaf points collecting api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf point collection api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_EARN_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf point collection api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf point collection api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS

            logger.error("Error in qitaf point collection api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf point collection api: {}".format(e)
            logger.error("Exception in qitaf point collection api: "
                         "{}".format(e))
            return {"error": error}, self.QITAF_CONNECTION_ERROR

    def redeem_points(self, data):
        """
        calls qitaf points redeem api

        "amount":100,
        "pin_number": 1231,
        "mobile_number":551601275,
        """
        try:
            self.request_data = data

            self.transaction_obj = self.request_data.get('transaction_obj')
            self.transaction_id = self.transaction_obj.transaction_id
            payload = self.request_data
            payload.pop('transaction_obj')
            url = self.qitaf_config.domain + QITAF_REDEEM_POINTS_API
            headers = self.get_payment_header()
            logger.info(
                "Youpay sending request data to qitaf redeem point api "
                "is {}".format(payload))
            response = requests.post(url, data=json.dumps(payload),
                                     headers=headers)
            logger.info("Response from qitaf redeem point api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf redeem point api response: {}".format(
                    response_data))
                self.response_data = response_data
                return response_data, self.SUCCESS

            logger.error("Error in qitaf redeem point api, {}"
                         "".format(response.text))
            self.response_data = response.json()
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf redeem point api: {}".format(e)
            logger.error("Exception in qitaf redeem point api: "
                         "{}".format(e))
            return {"error": error}, self.QITAF_CONNECTION_ERROR

        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(self.request_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_REDEMPTION,
            )

    def reverse_points(self, data):
        """
        calls qitaf points reverse api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf reverse point api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_REVERSE_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf reverse point api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf reverse point api response: {}".format(
                    response_data))
                self.response_data = response_data

                return response_data, self.SUCCESS

            logger.error("Error in qitaf reverse point api, {}"
                         "".format(response.text))
            self.response_data = response.json()
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf reverse point api: {}".format(e)
            logger.error("Exception in qitaf reverse point api: "
                         "{}".format(e), exc_info=True)
            return {"error": error}, self.QITAF_CONNECTION_ERROR

    def reward_update(self, data):
        """
        calls qitaf reward update api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf reward update api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_REWARD_UPDATE_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf reward update api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf reward update api response: {}".format(
                    response_data))
                return response_data, self.SUCCESS

            logger.error("Error in qitaf reward update api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.QITAF_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf reward update api: {}".format(e)
            logger.error("Exception in qitaf reward update api: "
                         "{}".format(e))
            return {"error": error}, self.QITAF_CONNECTION_ERROR
