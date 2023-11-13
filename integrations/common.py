import logging

import requests

from integrations.constants import ORDER_DETAILS_API

logger = logging.getLogger(__name__)


class WebhookDataFormat(object):

    def get_issuer_bank(self, response_data):
        issuer_bank = response_data.get("source", {}).get("issuer")
        return issuer_bank

    def get_three_ds(self, response_data):
        three_ds = response_data.get("3ds", {}).get("challenged")
        return three_ds

    def get_cvv_check(self, response_data):
        cvv_check = response_data.get("source", {}).get("cvv_check")
        return cvv_check

    def get_card_type(self, response_data):
        card_type = response_data.get("source", {}).get("card_type")
        return card_type


def update_brand_details(transaction_obj):
    """
    to get the order details from the client
    """
    try:

        if transaction_obj:
            client = transaction_obj.api_client
            api_key = client.api_key
            api_secret = client.api_secret
            invoice = transaction_obj.invoice_id
            transaction_id = transaction_obj.transaction_id

            headers = {
                'API-KEY': api_key,
                'API-SECRET': api_secret
            }
            logger.info("Fetching brand details from client started for "
                        "transaction  {}".format(transaction_id))

            url = client.client_domain + ORDER_DETAILS_API + invoice
            response = requests.get(url, headers=headers)

            if response:
                response_data = response.json()
                transaction_obj.brand_details = response_data
                transaction_obj.save()
                return True
            else:
                logger.error(
                    "Unable to get response on brand details for "
                    "transaction {}".format(transaction_id))
                return False
        else:
            logger.error(
                "Transaction not found while fetching brand details")
            return False

    except Exception as e:
        logger.error(
            "Getting brand details failed with error {}".format(str(e)))
        return False
