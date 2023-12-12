import logging

import requests

from core.constants import PRODUCT_GROUP_GIFT_CODE

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
            brand_details_path = client.brand_details_path
            invoice = transaction_obj.invoice_id
            transaction_id = transaction_obj.transaction_id

            if transaction_obj.api_client.client_code == PRODUCT_GROUP_GIFT_CODE:
                brand_details = prepare_brand_item_set(transaction_obj)
                transaction_obj.brand_details = brand_details
                logger.info(
                    "Brand details prepaired for transaction {} is {}".format(
                        transaction_id, brand_details
                    ))
                transaction_obj.save()
                return True

            if not brand_details_path:
                logger.error("Brand details path not found for client {} for"
                             " transaction {}".format(client.name,
                                                      transaction_id))
                return False

            headers = {
                'API-KEY': api_key,
                'API-SECRET': api_secret
            }

            url = client.client_domain + brand_details_path + invoice
            logger.info("Fetching brand details from client {} started for "
                        "transaction {}".format(url, transaction_id))
            response = requests.get(url, headers=headers)

            if response:
                response_data = response.json()
                transaction_obj.brand_details = response_data
                logger.info(
                    "Brand details response for transaction {} is {}".format(
                        transaction_id, response_data
                    ))
                transaction_obj.save()
                return True
            else:
                logger.error(
                    "Unable to get response on brand details for "
                    "transaction {}, error : {}".format(transaction_id,
                                                        response.text))
                return False
        else:
            logger.error(
                "Transaction not found while fetching brand details")
            return False

    except Exception as e:
        logger.error(
            "Getting brand details failed with error {}".format(str(e)))
        return False


def prepare_brand_item_set(transaction_obj):
    """
    This method will prepare brand item set, for now Groupgift has only
    one brand item set, so no need to call brand item details api
    instead just prepare an item set with the data which we have

    item set structure :
    {
        "currency": "SAR",
        "item_set": [
            {
                "vat": 0.97,
                "item_id": "#line-TCYSA-14_39_58-a9817764-f0c5-4d37-9e56-e171088f36cd",
                "quantity": 1,
                "brand_code": "TCYSA",
                "service_charge": 6.44,
                "gift_base_value": 50.0
            }
        ]
    }

    """
    brand_details = {
        "currency": transaction_obj.currency,
        "item_set": [
            {
                "vat": float(transaction_obj.VAT_amount),
                "item_id": "",
                "quantity": 1,
                "brand_code": "",
                "service_charge": float(transaction_obj.service_fee),
                "gift_base_value": float(transaction_obj.base_amount)
            }
        ],
        "comments": "calulated by youpay"
    }

    return brand_details
