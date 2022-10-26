import logging
import json
import requests

from django.conf import settings
from rest_framework.views import APIView
from services.v1.constants import ( B2C_PAYBACK_YOUPAY_PRODUCT_CODE,
                                    B2C_PAYBACK_CONFIG_ENDPOINT,
                                    B2C_PAYBACK_GATEWAY_CODE
                                    )
from integrations.models import PaymentGateway

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
        b2c_gateway_obj = PaymentGateway.objects.get(
            code=B2C_PAYBACK_GATEWAY_CODE)
        b2c_payback_domain = b2c_gateway_obj.domain
        url = b2c_payback_domain + B2C_PAYBACK_CONFIG_ENDPOINT
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, data=request_data_json,
                                     headers=headers)
            return response.json()
        except Exception as e:
            logger.error("config api call to b2cpayback failed", exc_info=e)
            return None
