import json
import requests
import logging

from django.conf import settings
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from services.v1.constants import B2C_PAYBACK_YOUPAY_PRODUCT_CODE
from integrations.constants import (ADCB_POINT_BALANCE_API,
                                    B2CPAYBACK_HUB_CODE,
                                    B2CP_CACHE_KEY,
                                    ADCB_AUTHENTICATE_API,
                                    ADCB_REDEMPTION_API)
# from .utils import get_payement_gateway
from core.utils import get_payment_gateway_config

logger = logging.getLogger(__name__)


class B2CPaybackManager(PaymentRequestView, PaymentHandlers):
    """
    Class to manage b2cpayback related operations
    """

    def get_configurations(self, amount, currency):

        # TODO - get amount, currency from the youpay transaction data

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
        url = b2c_payback_domain + '/payback/api/v1/configuration/'
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=headers)
            return response.json()
        except Exception as e:
            response = None
            logger.error("config api call to b2cpayback failed", exc_info=e)
            return None

    def get_point_balance(self):

        point_balance_request_data = {
            "card_no": "5420187505091559",
            "expiry": "2402",
            "customer_name": "jomon",
            "client_code": "ADCBTP",
            "invoice_id": "35023",
            "platform": "Web"
        }
        request_data_json = json.dumps(point_balance_request_data)

        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + ADCB_POINT_BALANCE_API

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=headers)
            return response.json()
        except Exception as e:
            response = None
            logger.error("point balance api call to b2cpayback failed {}".format(str(e)))
            return None

    def authenticate_redemption(self):

        authenticate_request_data = {
          "card_type": "Visa",
          "cko-card-token": "tok_plne6tjxnkzezigws6sxwzy3ba",
          "customer_email": "jomon+pb@yougotagift.com",
          "is_save_user_token": False,
          "response_url": "http://192.168.225.176:12000/checkout/invoices/34932/payback/verification/",
          "client_code": "ADCBTP",
          "token_type": "card",
          "platform": "Web",
          "reference_id": "NS4N2GFYPJFJCV",
          "invoice_amount": "107.88",
          "channel_code": "YGAGAE",
          "redemption_amount": "107.88",
          "redemption_currency": "AED",
          "customer_ip_address": "84.226.122.71",
          "selected_amount": "107.88",
          "invoice_id": "35023"
        }
        request_data_json = json.dumps(authenticate_request_data)

        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + ADCB_AUTHENTICATE_API

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=headers)
            return response.json()
        except Exception as e:
            response = None
            logger.error(
                "authenticate api call to b2cpayback failed {}".format(
                    str(e)))
            return None

    def point_redemption(self):

        redemption_request_data = {
                  "reference_id": "NS4N2GFYPJFJCV",
                  "request_id": "HFTBIAXG5QH3GDKD",
                  "otp_reference_number": "33449757",
                  "platform": "Web",
                  "client_code": "ADCBTP",
                  "authentication_code": "11111111"
                }

        request_data_json = json.dumps(redemption_request_data)

        b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                     B2CPAYBACK_HUB_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + ADCB_REDEMPTION_API

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=headers)
            return response.json()
        except Exception as e:
            response = None
            logger.error(
                "redemption api call to b2cpayback failed {}".format(
                    str(e)))
            return None