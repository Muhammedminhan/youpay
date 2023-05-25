import json
import logging
import requests

from core.utils import get_payment_gateway_config
from integrations.constants import (
    QITAF_OTP_GENERATION_API, QITAF_EARN_POINTS_API, QITAF_REDEEM_POINTS_API,
    QITAF_REVERSE_POINTS_API, QITAF_REWARD_UPDATE_API, QITAF_CACHE_KEY,
    QITAF_HUB_CODE
)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class QitafServiceManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage qitaf related operations
    """

    def __init__(self):
        self.qitaf_config = get_payment_gateway_config(QITAF_CACHE_KEY,
                                                       QITAF_HUB_CODE)

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
            logger.info(
                "Youpay sending request data to qitaf generate otp api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_OTP_GENERATION_API
            headers = self.get_payment_header()

            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from Qitaf service {}".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf payment response: {}".format(
                    response_data))
                if response.status == 200:
                    return response_data, self.SUCCESS

                logger.error("Error in qitaf otp, {}".format(response.text))
                return ({"error": response.text},
                        self.Qitaf_CONNECTION_ERROR)
            logger.error("Error in qitaf otp, {}".format(response.text))
            return ({"error": response.text},
                    self.Qitaf_CONNECTION_ERROR)

        except Exception as e:
            error = "Error in qitaf generate otp api: {}".format(e)
            logger.error("Exception in qitaf payment: {}".format(e))
            return {"error": error}, self.Qitaf_CONNECTION_ERROR

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
                if response.status == 200:
                    return response_data, self.SUCCESS

                logger.error("Error in qitaf point collection api, {}"
                             "".format(response.text))
                return {"error": response.text}, self.Qitaf_CONNECTION_ERROR
            logger.error("Error in qitaf point collection api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.Qitaf_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf point collection api: {}".format(e)
            logger.error("Exception in qitaf point collection api: "
                         "{}".format(e))
            return {"error": error}, self.Qitaf_CONNECTION_ERROR

    def redeem_points(self, data):
        """
        calls qitaf points redeem api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to qitaf redeem point api "
                "is {}".format(request_data))
            payload = json.dumps(request_data)
            url = self.qitaf_config.domain + QITAF_REDEEM_POINTS_API
            headers = self.get_payment_header()
            response = requests.post(url, data=payload, headers=headers)
            logger.info("Response from qitaf redeem point api {}"
                        "".format(response))
            if response:
                response_data = response.json()
                logger.info("qitaf redeem point api response: {}".format(
                    response_data))
                if response.status == 200:
                    return response_data, self.SUCCESS

                logger.error("Error in qitaf redeem point api, {}"
                             "".format(response.text))
                return {"error": response.text}, self.Qitaf_CONNECTION_ERROR
            logger.error("Error in qitaf redeem point api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.Qitaf_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf redeem point api: {}".format(e)
            logger.error("Exception in qitaf redeem point api: "
                         "{}".format(e))
            return {"error": error}, self.Qitaf_CONNECTION_ERROR

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
                if response.status == 200:
                    return response_data, self.SUCCESS

                logger.error("Error in qitaf reverse point api, {}"
                             "".format(response.text))
                return {"error": response.text}, self.Qitaf_CONNECTION_ERROR
            logger.error("Error in qitaf reverse point api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.Qitaf_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf reverse point api: {}".format(e)
            logger.error("Exception in qitaf reverse point api: "
                         "{}".format(e))
            return {"error": error}, self.Qitaf_CONNECTION_ERROR

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
                if response.status == 200:
                    return response_data, self.SUCCESS

                logger.error("Error in qitaf reward update api, {}"
                             "".format(response.text))
                return {"error": response.text}, self.Qitaf_CONNECTION_ERROR
            logger.error("Error in qitaf reward update api, {}"
                         "".format(response.text))
            return {"error": response.text}, self.Qitaf_CONNECTION_ERROR

        except Exception as e:
            error = "Error in qitaf reward update api: {}".format(e)
            logger.error("Exception in qitaf reward update api: "
                         "{}".format(e))
            return {"error": error}, self.Qitaf_CONNECTION_ERROR
