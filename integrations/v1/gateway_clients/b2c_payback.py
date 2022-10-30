import logging
import json
import requests
import logging

from django.conf import settings
from rest_framework.views import APIView
from services.v1.constants import ( B2C_PAYBACK_YOUPAY_PRODUCT_CODE,
                                    B2C_PAYBACK_CONFIG_ENDPOINT
                                    )
from integrations.models import PaymentGateway
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from services.v1.constants import B2C_PAYBACK_YOUPAY_PRODUCT_CODE
from integrations.constants import (ADCB_POINT_BALANCE_API,
                                    B2CPAYBACK_HUB_CODE,
                                    B2CP_CACHE_KEY,
                                    ADCB_AUTHENTICATE_API,
                                    ADCB_REDEMPTION_API, ADCB_HEADERS)
from core.utils import get_payment_gateway_config, get_app_config

logger = logging.getLogger(__name__)


class B2CPaybackManager(APIView):
    """
    Class to manage b2cpayback related operations
    """

    def get_configurations(self, amount, currency):
        product_code = B2C_PAYBACK_YOUPAY_PRODUCT_CODE
        amount = str(amount)
        currency = str(currency)
        config_request_data = {
            "amount": amount, "currency": currency,
            "product_code": product_code
        }
        request_data_json = json.dumps(config_request_data)
        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + B2C_PAYBACK_CONFIG_ENDPOINT
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=ADCB_HEADERS)
            return response.json()
        except Exception as e:
            logger.error("config api call to b2cpayback failed", exc_info=e)
            return None

    def get_point_balance(self, request_data ):
        request_data_json = json.dumps(request_data)

        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + ADCB_POINT_BALANCE_API
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=ADCB_HEADERS)
            return response.json()
        except Exception as e:
            logger.error("point balance api call to b2cpayback failed "
                         "{}".format(str(e)))
            return None

    def authenticate_redemption(self, request_data):
        request_data_json = json.dumps(request_data)
        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + ADCB_AUTHENTICATE_API
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=ADCB_HEADERS)
            return response.json()
        except Exception as e:
            logger.error(
                "authenticate api call to b2cpayback failed {}".format(
                    str(e)))
            return None

    def point_redemption(self, request_data):
        request_data_json = json.dumps(request_data)
        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + ADCB_REDEMPTION_API
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=ADCB_HEADERS)
            return response.json()
        except Exception as e:
            logger.error(
                "redemption api call to b2cpayback failed {}".format(
                    str(e)))
            return None
