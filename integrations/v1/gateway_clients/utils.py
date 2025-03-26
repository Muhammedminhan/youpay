import json
import logging

import requests

from core.constants import PAYBACK_ACTION_EARN
from core.response_messages import YouPayResponse
from core.utils import get_payment_gateway_config, get_channel_code
from integrations.common import update_brand_details
from integrations.constants import (ADCB_CLIENT_CODE,
                                    ADCB_CHECKOUTPG_PAYMENT_NOT_PAID,
                                    CITI_REWARDS_OTP_EXPIRED_CODE,
                                    CITI_REWARDS_VALIDATION_ERROR_CODE,
                                    CITI_REWARDS_ALREADY_REDEEMED_CODE,
                                    CITI_REWARDS_INSUFFICIENT_BALANCE_CODE,
                                    CITI_REWARDS_INVALID_CUSTOMER_CODE,
                                    PAYMENT_REQUEST_POINT_BALANCE,
                                    CITI_REWARDS_ACCOUNT_LOCKED_ERROR_CODE,
                                    QITAF_CALCULATE_BALANCE_API,
                                    B2CP_CACHE_KEY, B2CPAYBACK_HUB_CODE,
                                    SPONSOR_PAYMENT_NETWORK_PERCENTAGE,
                                    SPONSOR_PAYMENT_NETWORK_VALUE,
                                    CLIENT_CODE_MAPPING,
                                    CLIENT_CODE_MAPPING_ARABIC
                                    )
from payments.models import YouPayTransactionData
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


def get_saved_fields(saved_fields, data_dict, payment_transaction):
    for key, value in data_dict.items():
        if value:
            payment_transaction.__dict__[key] = value
            saved_fields.append(key)

    return saved_fields


def get_transaction_object(transaction_id):
    """
    Method for retrieve transaction object
    """
    transaction_object = YouPayTransactionData.objects.get(
        transaction_id=transaction_id)
    return transaction_object


def update_transaction_object(data):
    data_dict = {}
    transaction_id = data.get('id', None)
    data_dict['approved'] = data.get('approved', None)
    try:
        payment_transaction = get_transaction_object(
            transaction_id)
        saved_fields = ['api_response_data', 'modified_on']
        if payment_transaction:
            saved_fields = get_saved_fields(saved_fields,
                                            data_dict,
                                            payment_transaction)
            payment_transaction.save(update_fields=saved_fields)

    except Exception as e:
        logger.error(
            "while update youpa transaction got exception {0}".format(
                str(e)))


def format_adcb_point_balance_data(request_data, transaction_obj):
    request_data['customer_name'] = transaction_obj.customer_name
    request_data['client_code'] = ADCB_CLIENT_CODE
    request_data['invoice_id'] = transaction_obj.invoice_id
    request_data['platform'] = transaction_obj.platform
    return request_data


def format_adcb_authenticate_data(request_data, transaction_obj):
    request_data['is_save_user_token'] = False
    request_data['client_code'] = ADCB_CLIENT_CODE
    request_data['platform'] = transaction_obj.platform
    request_data['invoice_amount'] = str(transaction_obj.amount)
    request_data['channel_code'] = transaction_obj.channel_code
    request_data['invoice_id'] = transaction_obj.invoice_id
    request_data['customer_ip_address'] = transaction_obj.ip
    return request_data


def format_adcb_redemption_data(request_data, transaction_obj):
    request_data['platform'] = transaction_obj.platform
    request_data['client_code'] = ADCB_CLIENT_CODE
    return request_data


def format_adcb_verify_data(request_data, transaction_obj):
    request_data['invoice_id'] = transaction_obj.invoice_id
    request_data['channel_code'] = get_channel_code(transaction_obj)
    return request_data


def format_verify_data(request_data, transaction_obj):
    request_data['invoice_id'] = transaction_obj.invoice_id
    request_data['channel_code'] = get_channel_code(transaction_obj)
    return request_data


def get_adcb_verify_redirect_url(response_data,
                                 transaction_obj):  # partial redemption
    payment_status = response_data.get("results", {}).get("payment_status")
    redemption_status = (
        response_data.get("results", {}).get("redemption_status"))

    if payment_status and redemption_status:
        logger.info("Partial payment through card and touchpoints for id "
                    "{}".format(transaction_obj.transaction_id))
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id, True)
    elif payment_status and not redemption_status:
        logger.info("Full amount paid through card for id {}".format(
            transaction_obj.transaction_id))
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id, True)
    elif ("results" not in response_data and
          response_data.get("code") == ADCB_CHECKOUTPG_PAYMENT_NOT_PAID):
        logger.info(
            "Transaction failed at checkout for transaction id {}, failure "
            "url {}".format(transaction_obj.transaction_id,
                            transaction_obj.failure_url))
        response_data["is_redirect"] = False
        redirect_url = None
        return get_adcb_response_url(redirect_url,
                                     transaction_obj.transaction_id, False)
    else:
        logger.info("Transaction failed for transaction id {}, failure url "
                    "{}".format(transaction_obj.transaction_id,
                                transaction_obj.failure_url))
        return get_adcb_response_url(
            transaction_obj.failure_url,
            transaction_obj.transaction_id, False)


def get_qitaf_verify_redirect_url(response_data, transaction_obj):
    payment_status = response_data.get("results", {}).get("payment_status")
    redemption_status = (
        response_data.get("results", {}).get("redemption_status"))

    if payment_status and redemption_status:
        logger.info("Partial payment through card and touchpoints for id "
                    "{}".format(transaction_obj.transaction_id))
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id, True)
    elif payment_status and not redemption_status:
        logger.info("Full amount paid through card for id {}".format(
            transaction_obj.transaction_id))
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id, True)
    elif ("results" not in response_data and
          response_data.get("code") == ADCB_CHECKOUTPG_PAYMENT_NOT_PAID):
        logger.info(
            "Transaction failed at checkout for transaction id {}, failure "
            "url {}".format(transaction_obj.transaction_id,
                            transaction_obj.failure_url))
        response_data["is_redirect"] = False
        redirect_url = None
        return get_adcb_response_url(redirect_url,
                                     transaction_obj.transaction_id, False)
    else:
        logger.info("Transaction failed for transaction id {}, failure url "
                    "{}".format(transaction_obj.transaction_id,
                                transaction_obj.failure_url))
        return get_adcb_response_url(
            transaction_obj.failure_url,
            transaction_obj.transaction_id, False)


def get_adcb_redemption_redirect_url(response_data,
                                     transaction_obj):  # full redemption
    if response_data.get('results', {}).get('redemption_status'):
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id, True)
    else:
        return get_adcb_response_url(
            transaction_obj.failure_url, transaction_obj.transaction_id,
            False)


def get_adcb_response_url(url, transaction_id, status):
    if url:
        return_url = url + '?transaction_id=' + str(transaction_id)
    else:
        return_url = None
    return return_url, status


def get_citi_converted_amount(response_data, amount):
    """
    will convert the amount to citi rewards
    points based on the ratio
    """
    from decimal import Decimal
    if response_data.get('conversion_rate'):
        amount_conversion_rate = Decimal(response_data.get('conversion_rate'))
        converted_points = int(round(amount / amount_conversion_rate))
        return converted_points
    return None


def format_citi_service_error_response(response_data, api_type):
    """
    check the response code from b2cpayback
    returns corresponding response from youpay
    """
    response_manager = YouPayResponse()
    if 'errors' in response_data:
        code = response_data.get('errors').get('code')
        if (
                api_type == PAYMENT_REQUEST_POINT_BALANCE and
                code == CITI_REWARDS_VALIDATION_ERROR_CODE
        ):
            return response_manager.CITI_REWARDS_INVALID_OTP
        error_dict = {
            CITI_REWARDS_OTP_EXPIRED_CODE: (
                response_manager.CITI_REWARDS_OTP_EXPIRED_OR_ATTEMPTS_EXCEEDED
            ),
            CITI_REWARDS_VALIDATION_ERROR_CODE: (
                response_manager.CITI_REWARDS_VALIDATION_ERROR),
            CITI_REWARDS_ALREADY_REDEEMED_CODE: (
                response_manager.CITI_REWARDS_ALREADY_REDEEMED
            ),
            CITI_REWARDS_INSUFFICIENT_BALANCE_CODE: (
                response_manager.CITI_REWARDS_INSUFFICIENT_BALANCE
            ),
            CITI_REWARDS_INVALID_CUSTOMER_CODE: (
                response_manager.CITI_REWARDS_INVALID_CUSTOMER
            ),
            CITI_REWARDS_ACCOUNT_LOCKED_ERROR_CODE: (
                response_manager.CITI_REWARDS_USER_BLOCKED
            )
        }
        if code in error_dict:
            return error_dict[code]
    return response_manager.CITI_REWARDS_CONNECTION_ERROR


def calculate_balance(data):
    """
    Calculate service charge
    """
    response_obj = YouPayResponse()
    b2c_config = get_payment_gateway_config(B2CP_CACHE_KEY,
                                            B2CPAYBACK_HUB_CODE)
    crud_obj = YouPayTransactionCRUD()
    try:
        transaction_obj = data.get('transaction_obj')
        selected_amount = data.get('selected_amount')
        client_code = data.get("client_code")

        payment_reference = transaction_obj.payment_reference

        transaction_id = transaction_obj.transaction_id

        is_updated, brand_details = update_brand_details(transaction_obj)

        items_array = brand_details.get("item_set", None)

        if not items_array or not len(items_array) or not is_updated:
            logger.error("Brand details not found for transaction {}"
                         "".format(transaction_obj.transaction_id))
            return None, response_obj.BRAND_DETAILS_MISSING

        payload = json.dumps({
            "payment_reference": payment_reference,
            "item_details_list": items_array,
            "currency": brand_details.get("currency"),
            "selected_amount": selected_amount,
            "client_code": client_code,
            "payback_action": data.get("payback_action"),
        })

        url = b2c_config.domain + QITAF_CALCULATE_BALANCE_API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': b2c_config.api_key,
            'X-API-KEY': b2c_config.api_key
        }
        response = requests.post(url, data=payload, headers=headers)

        logger.info(
            "Calculate balance api payload {}, response {} for transaction"
            " {}".format(payload, response.json(), transaction_id))

        response_data = None
        response_code = response_obj.QITAF_BALANCE_CALCULATION_FAILED
        if response:
            response_data = response.json()
            if response_data.get('status', False):
                calculated_balance = response_data.get(
                    'calculated_item_details')
                apply_offer_if_needed(data, transaction_obj,
                                      calculated_balance, client_code)

                update_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    "brand_details": brand_details,
                    "brand_calculations": calculated_balance
                }
                crud_obj.update_youpay_transaction_data(update_data)
                response_code = response_obj.SUCCESS
        return response_data, response_code

    except Exception as e:
        logger.error("Exception in calculate_balance: "
                     "{}".format(e), exc_info=True)
        return None, response_obj.QITAF_BALANCE_CALCULATION_FAILED


def apply_offer_if_needed(data, transaction_obj, calculated_balance,
                          client_code):
    """Apply offer details if the payback action is not earn"""
    if data.get("payback_action") == PAYBACK_ACTION_EARN:
        return

    transaction_object = YouPayTransactionCRUD()
    offer_details = transaction_object.get_offer_details(transaction_obj)
    if offer_details:
        program_offer = offer_details.get(client_code)
        if program_offer:
            process_offer_eligibility(calculated_balance, program_offer,
                                    client_code)


def process_offer_eligibility(calculated_balance, program_offer, client_code):
    """
    Evaluates whether an offer is applicable for each brand in the calculated item details.
    """
    try:
        calculated_item_details = calculated_balance.get(
            'calculated_item_details', [])
        paid_by_points = calculated_balance.get('sum_redemption_points', 0)
        for offer in program_offer:
            calculated_threshold, grouped_calculated_item_details = (
                find_threshold_amount_from_calc_balance(
                    offer, calculated_item_details))

            for calculated_item in grouped_calculated_item_details:
                is_offer_applicable, message, message_ar = check_offer_eligibility(
                    calculated_threshold, paid_by_points, client_code
                )

                calculated_item.update({
                    'is_offer_applicable': is_offer_applicable,
                    'offer_text': offer.get("offer_text"),
                    'brand_logo': offer.get("brand_logo"),
                    'brand_name': offer.get("brand_name"),
                    'offer_error_message': message,
                    'offer_error_message_ar': message_ar,
                    'offer_code': offer.get("offer_code"),
                })

    except Exception as e:
        logger.exception(
            f"An error occurred in process_offer_eligibility: {e}")


def check_offer_eligibility(calculated_threshold, paid_by_points,
                            client_code):
    """
    Determines whether an offer is applicable based on sponsor payment threshold type.
    """
    is_offer_applicable = False
    if calculated_threshold <= paid_by_points:
        is_offer_applicable = True

    message = None
    message_ar = None
    if not is_offer_applicable:
        client_program_name = CLIENT_CODE_MAPPING.get(client_code,
                                                      "Redemption")
        client_program_name_ar = CLIENT_CODE_MAPPING_ARABIC.get(client_code,
                                                                "Redemption")
        message = f"Redeem at least SAR {calculated_threshold} in {client_program_name} points to claim the offer"
        message_ar = f"استردّ ما لا يقل عن {calculated_threshold} ريال سعودي من نقاط {client_program_name_ar} للاستفادة من العرض."

    return is_offer_applicable, message, message_ar


def find_threshold_amount(offer_details, transaction_obj):
    threshold_type = offer_details.get("sponsor_payment_threshold_type")
    threshold = float(offer_details.get("sponsor_payment_threshold", 0))
    offer_brand = offer_details.get("brand_code")
    item_set = transaction_obj.brand_details.get("item_set")
    total_quantity = 0
    total_brand_value = 0

    for item in item_set:
        if item["brand_code"] == offer_brand:
            total_quantity += item["quantity"]
            total_brand_value += item["quantity"] * item["gift_base_value"]

    if threshold_type == SPONSOR_PAYMENT_NETWORK_PERCENTAGE:
        calculated_threshold = round(threshold * total_brand_value / 100)

    elif threshold_type == SPONSOR_PAYMENT_NETWORK_VALUE:
        calculated_threshold = round(total_quantity * threshold)
    else:
        calculated_threshold = None
        logger.error("Invalid sponsor payment threshold type")
    return calculated_threshold


def find_threshold_amount_from_calc_balance(offer_details,
                                            calculated_item_details):
    threshold_type = offer_details.get("sponsor_payment_threshold_type")
    threshold = float(offer_details.get("sponsor_payment_threshold", 0))
    offer_brand = offer_details.get("brand_code")
    total_quantity = 0
    total_brand_value = 0
    grouped_calculated_item_details = []

    for item in calculated_item_details:
        if item["brand_code"] == offer_brand:
            total_quantity += item["quantity"]
            total_brand_value += item["quantity"] * item["gift_base_value"]
            grouped_calculated_item_details.append(item)

    if threshold_type == SPONSOR_PAYMENT_NETWORK_PERCENTAGE:
        calculated_threshold = round(threshold * total_brand_value / 100)

    elif threshold_type == SPONSOR_PAYMENT_NETWORK_VALUE:
        calculated_threshold = round(total_quantity * threshold)
    else:
        calculated_threshold = None
        logger.error("Invalid sponsor payment threshold type")
    return calculated_threshold, grouped_calculated_item_details


def process_calculated_item_details(data):
    required_keys = {
        "brand_code",
        "is_offer_applicable",
        "offer_text",
        "brand_logo",
        "brand_name",
        "offer_error_message",
        "offer_error_message_ar",
        "offer_code",
    }
    unique_brands = {}
    for item in data.get("calculated_item_details", {}):
        brand_code = item.get("brand_code")
        if brand_code not in unique_brands:
            unique_brands[brand_code] = {key: item[key] for key in
                                         required_keys if key in item}

    data["calculated_item_details"] = list(unique_brands.values())
    return data
