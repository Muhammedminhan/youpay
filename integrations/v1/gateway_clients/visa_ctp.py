from jwcrypto import jwe, jwk
import json
import logging

import requests

from core.constants import EXTERNAL_API_REQUEST_TIMEOUT, REQUEST_METHOD_POST, \
    REQUEST_METHOD_GET
from core.response_messages import YouPayResponse
from core.utils import get_app_config, get_payment_gateway_config
from integrations.constants import (VISACTP_CACHE_KEY, VISACTP_CLIENT_CODE,
                                    VISACTP_PAYMENT_TYPE, VISACTP_SESSION_API,
                                    VISACTP_ALLOWED_CARDS,
                                    PAYMENT_REQUEST_VISA_SESSION,
                                    VISACTP_CREDENTIALS_API,
                                    PAYMENT_REQUEST_VISA_CREDENTIALS,
                                    VISACTP_TOKEN_TYPE)
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from payments.serializers.youpay_payments import \
    YouPayTransactionDataSerializer
from services.constants import TOKEN_TYPE_VISACTP
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class VisaManager(YouPayResponse, PaymentHandlers):
    def __init__(self):
        super(VisaManager, self).__init__()

    def create_visa_session(self, transaction_obj):
        """
        Method for creating a Visa Click to Pay session (Capture Context)
        """
        try:
            app_config = get_app_config()
            if not app_config:
                logger.error("Visa session failed: No site configuration found.")
                return None, self.PAYMENT_FAILED

            target_origin = app_config.front_end_domain.rstrip('/')

            visa_config = get_payment_gateway_config(
                VISACTP_CACHE_KEY, VISACTP_CLIENT_CODE)
            if not visa_config:
                logger.error("Visa gateway configuration missing.")
                return None, self.PAYMENT_FAILED

            auth_token = visa_config.api_key
            allowed_cards = visa_config.validation_json.get('allowed_cards',
                                VISACTP_ALLOWED_CARDS)

            url = visa_config.domain + VISACTP_SESSION_API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json"
            }
            request_data = {
                "targetOrigins": [target_origin],
                "allowedCardNetworks": allowed_cards,
                "allowedPaymentTypes": VISACTP_PAYMENT_TYPE,
                "data": {
                    "orderInformation": {
                        "amountDetails": {
                            "totalAmount": str(transaction_obj.amount),
                            "currency": transaction_obj.currency
                        }
                    }
                }
            }

            response = requests.post(
                url,
                data=json.dumps(request_data),
                headers=headers,
                timeout=EXTERNAL_API_REQUEST_TIMEOUT
            )

            self.create_youpay_to_payment_gateways_data(
                transaction_obj=transaction_obj,
                transaction_id=transaction_obj.transaction_id,
                request_data=json.dumps(request_data),
                response_data=response.text,
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_VISA_SESSION,
            )

            if response.status_code in [200, 201]:
                response_data = response.json()
                return {'visa_session_token': response_data.get(
                    'captureContext')}, self.SUCCESS

            logger.error(
                f"Visa session creation failed. Status: {response.status_code}, "
                f"Transaction: {transaction_obj.transaction_id}, Response: "
                f"{response.text}"
            )
            return None, self.VISACTP_SESSION_FAILED

        except Exception as e:
            logger.exception(f"Exception in Visa session creation: {str(e)}")
            return None, self.VISACTP_CONNECTION_ERROR

    def process_visa_payment(self, transaction_obj, visa_transient_token):
        """
        Handles the Visa payment flow:
        Visa Payload Fetch -> Decryption -> Checkout.com Payment
        """
        try:
            visa_config = get_payment_gateway_config(
                VISACTP_CACHE_KEY, VISACTP_CLIENT_CODE)
            auth_token = visa_config.api_key

            visa_url = (visa_config.domain + VISACTP_CREDENTIALS_API + "/" +
                        visa_transient_token)
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            visa_response = requests.get(visa_url, headers=headers,
                timeout=EXTERNAL_API_REQUEST_TIMEOUT)

            self.create_youpay_to_payment_gateways_data(
                transaction_obj=transaction_obj,
                transaction_id=transaction_obj.transaction_id,
                request_data=json.dumps(
                    {"visa_transient_token": visa_transient_token}),
                response_data=visa_response.text,
                request_method=REQUEST_METHOD_GET,
                request_type=PAYMENT_REQUEST_VISA_CREDENTIALS,
            )

            if visa_response.status_code not in [200, 201]:
                logger.error(
                    f"Visa Credentials Fetch Failed. Status: "
                    f"{visa_response.status_code}, Transaction: "
                    f"{transaction_obj.transaction_id}, Response: "
                    f"{visa_response.text}"
                )
                return None, self.VISACTP_CARD_DETAILS_FAILED

            decrypted_data = self.decrypt_visa_payload(
                visa_response.text, visa_config)

            if not decrypted_data:
                return None, self.VISACTP_CARD_DETAILS_FAILED

            payment_info = decrypted_data.get('paymentInformation', {})
            card_data = payment_info.get('card', {})

            visa_request_data = {
                "source": {
                    "type": VISACTP_TOKEN_TYPE,
                    "token": card_data.get('number'),
                    "expiry_month": card_data.get('expirationMonth'),
                    "expiry_year": card_data.get('expirationYear'),
                    "cryptogram": card_data.get('cryptogram'),
                    "eci": card_data.get('eci')
                },
                "customer_name": transaction_obj.customer_name,
                "is_mada": False,
                "is_save_user_token": False
            }

            serializer = YouPayTransactionDataSerializer(transaction_obj)

            payment_payload = {
                'token_type': TOKEN_TYPE_VISACTP,
                'transaction_data': serializer.data,
                'request_data': visa_request_data,
                'transaction_obj': transaction_obj,
                'site_domain': get_app_config().front_end_domain
            }

            checkout = CheckoutpgManager()
            response_data, status_code = checkout.card_payment(payment_payload)

            return response_data, status_code

        except Exception as e:
            logger.exception(f"Exception in process_visa_payment: {str(e)}")
            return None, self.VISACTP_CONNECTION_ERROR

    def decrypt_visa_payload(self, jwe_string, visa_config):
        """
        Decrypts Visa JWE using RSA Private Key (Stored in api_secret).
        Returns decrypted JSON dictionary.
        """
        try:
            # The key must be in PEM format (-----BEGIN RSA PRIVATE KEY-----)
            private_key_pem = visa_config.api_secret

            # Create a JWK (JSON Web Key) object from the PEM
            key = jwk.JWK.from_pem(private_key_pem.encode('utf-8'))

            jwetoken = jwe.JWE()
            jwetoken.deserialize(jwe_string)
            jwetoken.decrypt(key)

            decrypted_payload = jwetoken.payload.decode('utf-8')

            logger.info("Visa JWE successfully decrypted.")
            return json.loads(decrypted_payload)

        except Exception as e:
            logger.error(f"JWE Decryption Failed: {str(e)}")
            return None
