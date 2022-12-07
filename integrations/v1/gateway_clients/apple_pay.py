import logging

import requests

from core.constants import PAYMENT_GATEWAY_APPLEPAY
from core.utils import get_payment_gateway_config
from integrations.constants import APPLE_PAY_CACHE_KEY, APPLE_PAY_HUB_CODE
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class ApplePayManager(PaymentRequestView, PaymentHandlers):

    def __init__(self):
        self.tabbypg_config = get_payment_gateway_config(APPLE_PAY_CACHE_KEY,
                                                         APPLE_PAY_HUB_CODE)
        self.transaction_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_APPLEPAY
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None
        self.request_data = None
        self.response_data = None
        self.request_type = None
        self.request_method = None
        self.transaction_obj = None

    def validate_session(self, request_data):
        logger.info("APPLE PAY Validating session")
        # self.request_data = request_data
        # self.request_method = REQUEST_METHOD_POST
        # self.request_type = 'validate_session'
        # self.transaction_id = request_data.get('transaction_id')
        # self.payment_method = request_data.get('payment_method')
        # self.channel_code = APPLE_PAY_HUB_CODE
        # self.transaction_obj = self.get_youpay_transaction_data(
        #     self.transaction_id)

        url = "http://localhost:8000/services/api/v1/test-payment/"

        payload = {
            "merchantIdentifier": "merchant.com.yougotagift.aed.sandbox",
            "domainName": "yougotagift.com",
            "displayName": "YouGotAGift",
        }
        print("payload", payload)

        cert_file = ("sample.pem", "sample.pem")
        print("cert_file", cert_file)

        print("Sending request to Apple Pay")
        response = requests.post(
            url,
            json=payload,
            cert=cert_file,
        )
        print("Response from Apple Pay", response)
        print("Response from Apple Pay", response.json())
        print("Applepay response ", response.text)

        return True

        if self.transaction_obj:
            return True
        return False
