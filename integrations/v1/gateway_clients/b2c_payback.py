import json
import requests

from django.conf import settings
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers
from services.v1.constants import B2C_PAYBACK_YOUPAY_PRODUCT_CODE
from integrations.models import PaymentGateway

class B2CPaybackManager(PaymentRequestView, PaymentHandlers):
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
        b2c_gateway_obj = PaymentGateway.objects.get(code="PAYMTB2CPBK")
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
