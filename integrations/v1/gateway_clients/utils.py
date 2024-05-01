import logging

from core.response_messages import YouPayResponse
from integrations.constants import (ADCB_CLIENT_CODE,
                                    ADCB_CHECKOUTPG_PAYMENT_NOT_PAID,
                                    CITI_REWARDS_OTP_EXPIRED_CODE,
                                    CITI_REWARDS_VALIDATION_ERROR_CODE,
                                    CITI_REWARDS_ALREADY_REDEEMED_CODE,
                                    CITI_REWARDS_INSUFFICIENT_BALANCE_CODE,
                                    CITI_REWARDS_INVALID_CUSTOMER_CODE,
                                    PAYMENT_REQUEST_POINT_BALANCE,
                                    CITI_REWARDS_ACCOUNT_LOCKED_ERROR_CODE,
                                    CHECKOUT_UAE_CHANNEL_CODE,
                                    CHECKOUT_SAUDI_CHANNEL_CODE
                                    )
from payments.models import YouPayTransactionData

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
    request_data['channel_code'] = CHECKOUT_UAE_CHANNEL_CODE
    return request_data


def format_qitaf_verify_data(request_data, transaction_obj):
    request_data['invoice_id'] = transaction_obj.invoice_id
    request_data['channel_code'] = CHECKOUT_SAUDI_CHANNEL_CODE
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
