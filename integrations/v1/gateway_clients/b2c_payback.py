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
                                    ADCB_REDEMPTION_API, ADCB_HEADERS,
                                    ADCB_CLIENT_CODE)
from core.utils import ( get_payment_gateway_config,
                         get_app_config, decrypt_string
                         )
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class B2CPaybackManager(APIView, YouPayTransactionCRUD):
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

    def get_point_balance(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                request_data['customer_name'] = transaction_obj.customer_name
                request_data['client_code'] = ADCB_CLIENT_CODE
                request_data['invoice_id'] = transaction_obj.invoice_id
                request_data['platform'] = transaction_obj.platform
                request_data_json = json.dumps(request_data)
                b2c_gateway_obj = get_payment_gateway_config(
                    B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE)
                b2c_payback_domain = b2c_gateway_obj.domain
                url = b2c_payback_domain + ADCB_POINT_BALANCE_API
                response = requests.post(url, data=request_data_json,
                                         headers=ADCB_HEADERS)
                return response.json(), transaction_obj.transaction_id
            except Exception as e:
                logger.error("point balance api call to b2cpayback failed ",
                             exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id received for point balance "
                         "api")
            return None , None


    def authenticate_redemption(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                request_data['customer_email'] = (
                    transaction_obj.customer_email
                )
                request_data['is_save_user_token'] = False
                request_data['client_code'] = ADCB_CLIENT_CODE
                request_data['platform'] = transaction_obj.platform
                request_data['invoice_amount'] = str(transaction_obj.amount)
                request_data['channel_code'] = transaction_obj.channel_code
                request_data['invoice_id'] = transaction_obj.invoice_id
                request_data['customer_ip_address'] = transaction_obj.ip
                request_data['token_type'] = transaction_obj.payment_method
                request_data['card_type'] = transaction_obj.payment_scheme
                request_data_json = json.dumps(request_data)
                b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                             B2CPAYBACK_HUB_CODE)
                b2c_payback_domain = b2c_gateway_obj.domain
                url = b2c_payback_domain + ADCB_AUTHENTICATE_API
                response = requests.post(url, data=request_data_json,
                                     headers=ADCB_HEADERS)
                return response.json(), transaction_obj.transaction_id
            except Exception as e:
                logger.error(
                    "authenticate api call to b2cpayback failed", exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id received for b2cpayback "
                         "authentication api")
            return None , None

    def point_redemption(self, request_data):
        request_transaction_id = request_data.get('transaction_id')
        if request_transaction_id:
            try:
                transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(request_transaction_id))
                request_data['platform'] = transaction_obj.platform
                request_data['client_code'] = ADCB_CLIENT_CODE
                request_data_json = json.dumps(request_data)
                b2c_gateway_obj = get_payment_gateway_config(B2CP_CACHE_KEY,
                                                             B2CPAYBACK_HUB_CODE)
                b2c_payback_domain = b2c_gateway_obj.domain
                url = b2c_payback_domain + ADCB_REDEMPTION_API
                response = requests.post(url, data=request_data_json,
                                         headers=ADCB_HEADERS)
                return response.json(), transaction_obj.transaction_id
            except Exception as e:
                logger.error(
                    "redemption api call to b2cpayback failed", exc_info=e)
                return None, None
        else:
            logger.error("Invalid transaction id received for b2cpayback "
                         "redemption api")
            return None , None
