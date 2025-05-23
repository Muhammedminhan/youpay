import logging

import requests

from payments.constants import (PAYMENT_METHOD_NEQATY,
                                PAYMENT_METHOD_NEQATY_AND_CARD)
from services.models import APIClient
from services.v1.views.common import YouPayTransactionCRUD

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
    status = False
    brand_details = None
    try:
        if transaction_obj:

            if transaction_obj.brand_details:
                status = True
                logger.info("Brand Details already exists for {}".format(
                    transaction_obj.transaction_id))

                return status, transaction_obj.brand_details

            client = transaction_obj.api_client
            api_key = client.api_key
            api_secret = client.api_secret
            brand_details_path = client.brand_details_path
            invoice = transaction_obj.invoice_id
            transaction_id = transaction_obj.transaction_id

            if not brand_details_path:
                logger.error("Brand details path not found for client {} for"
                             " transaction {}".format(client.name,
                                                      transaction_id))
                return status, brand_details

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
                status = True
                brand_details = response_data
            else:
                logger.error(
                    "Unable to get response on brand details for "
                    "transaction {}, error : {}".format(transaction_id,
                                                        response.text))
        else:
            logger.error(
                "Transaction not found while fetching brand details")
        return status, brand_details

    except Exception as e:
        logger.error(
            "Getting brand details failed with error {}".format(str(e)))
        return status, brand_details


def get_redemption_details(transaction_obj, updated_brand_calculations):
    """
    The idea is to replace the additional_data with the neqaty balance
     calculation response from the neqaty service
    """

    brand_calculations = updated_brand_calculations
    youpay_update_data = {}
    if brand_calculations:
        amount = brand_calculations.get('sum_net_amount', None)
        base_amount = brand_calculations.get('sum_gift_base_value',
                                             None)
        redeemed_amount = brand_calculations.get(
            'sum_redemption_points', None)
        redeemed_point = brand_calculations.get(
            'redeemPoints', None)
        payable_amount = brand_calculations.get(
            'sum_card_payment_amount', None)
        service_fee = brand_calculations.get(
            'sum_applied_service_charge', None)
        vat_amount = brand_calculations.get('sum_applied_vat', None)

        if amount != base_amount:
            payment_method = PAYMENT_METHOD_NEQATY_AND_CARD
        else:
            payment_method = PAYMENT_METHOD_NEQATY

        youpay_update_data = {
            'redeemed_amount': redeemed_amount,
            'redeemed_points': redeemed_point,
            'payable_amount': payable_amount,
            'service_fee': service_fee,
            'base_amount': base_amount,
            'VAT_amount': vat_amount,
            'payment_method': payment_method
        }
    else:
        logger.error(
            "Brand calculation is empty for transaction {}".format(
                transaction_obj.transaction_id
            ))
    return youpay_update_data


def update_offer_details(client_pk, invoice_id, offer_details):
    """
    Updates and stores offer details for a transaction.

    Parameters:
    - client_pk (int): Primary key of the `APIClient` model.
    - invoice_id (str): Invoice ID associated with the transaction.
    - offer_details (dict): Offer details to be stored.

    Process:
    - Retrieves the client instance using the provided primary key.
    - Prepares offer data including the invoice ID, offer details, and client reference.
    - Stores the offer details using the `YouPayTransactionCRUD` object.
    - Logs an error if the process fails.
    """
    transaction_crud_obj = YouPayTransactionCRUD()
    try:
        client = APIClient.objects.get(id=client_pk)
        invoice = invoice_id

        offer_data = {
            "invoice_id": invoice,
            "offer_details": offer_details,
            "client": client
        }
        transaction_crud_obj.create_offer_details(offer_data)


    except Exception as e:
        logger.error(
            "Getting offer details failed with error {}".format(str(e)))
