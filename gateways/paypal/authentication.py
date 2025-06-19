import json

import requests
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from core.utils import get_payment_gateway_config
from gateways.paypal.constants import PAYPAL_WEBHOOK_VERIFY_ENDPOINT
from gateways.paypal.models import PaymentAccessToken
from integrations.constants import PAYPAL_HUB_CODE, PAYPAL_CACHE_KEY


class PayPalWebhookAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for PayPal webhooks that verifies the signature
    """

    def authenticate(self, request):
        try:
            headers = request.headers

            # Required headers from webhook
            transmission_id = headers.get("Paypal-Transmission-Id")
            transmission_time = headers.get("Paypal-Transmission-Time")
            cert_url = headers.get("Paypal-Cert-Url")
            auth_algo = headers.get("Paypal-Auth-Algo")
            transmission_sig = headers.get("Paypal-Transmission-Sig")
            paypal_config = get_payment_gateway_config(PAYPAL_CACHE_KEY,
                                                       PAYPAL_HUB_CODE)
            webhook_id = paypal_config.webhook_api_key

            if not all([transmission_id, transmission_time, cert_url,
                        auth_algo, transmission_sig, webhook_id]):
                raise AuthenticationFailed("Missing PayPal webhook headers")

            # Access token (you should cache this or use a token retriever)
            access_token = PaymentAccessToken.get_paypal_access_token(paypal_config)

            # Prepare verification payload
            payload = {
                "transmission_id": transmission_id,
                "transmission_time": transmission_time,
                "cert_url": cert_url,
                "auth_algo": auth_algo,
                "transmission_sig": transmission_sig,
                "webhook_id": webhook_id,
                "webhook_event": request.data,
            }
            url = paypal_config.domain + PAYPAL_WEBHOOK_VERIFY_ENDPOINT
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload)
            )

            if response.status_code != 200:
                raise AuthenticationFailed("PayPal signature verification failed")

            verification_status = response.json().get("verification_status")
            if verification_status != "SUCCESS":
                raise AuthenticationFailed("Invalid PayPal webhook signature")

            return (None, None)

        except Exception as e:
            raise AuthenticationFailed(f"Webhook verification failed: {str(e)}")
