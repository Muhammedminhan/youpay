import logging
import requests
from ..choices import OrderAction
from ..constants import (
    NETWORK_API_KEY,
    NETWORK_OUTLET_ID,
    NETWORK_TENANT_REALM,
    get_base_url,
    get_identity_url
)


logger = logging.getLogger(__name__)


class NetworkPGClient:
    def __init__(self):
        self.api_key = NETWORK_API_KEY
        self.outlet_id = NETWORK_OUTLET_ID
        self.base_url = get_base_url()

    def get_access_token(self):
        """
        Retrieves the access token using the API key.
        """
        headers = {
            "accept": "application/vnd.ni-identity.v1+json",
            "authorization": f"Basic {self.api_key}",
            "content-type": "application/vnd.ni-identity.v1+json",
        }
        payload = {"realmName": NETWORK_TENANT_REALM}

        try:
            auth_url = get_identity_url()
            logger.info("Fetching Network access token from: %s", auth_url)
            response = requests.post(
                auth_url, json=payload, headers=headers, timeout=30
            )
            if response.status_code != 200:
                logger.error(
                    "Error fetching Network access token. Status: %s, "
                    "Response: %s",
                    response.status_code, response.text
                )
                return None

            return response.json().get("access_token")
        except requests.RequestException as e:
            logger.error("Error fetching Network access token: %s", e)
            return None

    def create_order(
        self,
        payment_data,
        action=OrderAction.SALE,
    ):
        """
        Initiates a payment order for Hosted Payment Page.
        """
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/transactions/outlets/{self.outlet_id}/orders"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.ni-payment.v2+json",
            "Accept": "application/vnd.ni-payment.v2+json",
        }

        minor_amount = payment_data.get('amount')
        currency = payment_data.get('currency')
        email = payment_data.get('email')
        customer_name = payment_data.get('customer_name')
        payment_reference = payment_data.get('payment_reference')
        redirect_url = payment_data.get('redirect_url')
        payload = {
            "action": action,
            "amount": {"currencyCode": currency, "value": minor_amount},
            "emailAddress": email,
            "merchantOrderReference": payment_reference,
            "billingAddress": {
                "firstName": customer_name,
                "city": "Dubai",
                "countryCode": "AE"
            },
            "merchantAttributes": {"redirectUrl": redirect_url}
        }

        try:
            logger.info("Creating Network order for reference: %s",
                        payment_reference)
            response = requests.post(url, json=payload, headers=headers,
                                     timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error creating Network order: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def get_order_status(self, order_id):
        """
        Retrieves the current status of an order.
        """
        token = self.get_access_token()
        if not token:
            return None

        url = (
            f"{self.base_url}/transactions/outlets/"
            f"{self.outlet_id}/orders/{order_id}"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.ni-payment.v2+json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Error fetching order status for %s: %s", order_id, e)
            return None
