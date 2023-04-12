import logging

from payments.models import YouPayTransactionData
from integrations.constants import (ADCB_CLIENT_CODE,
                                    ADCB_CHECKOUTPG_PAYMENT_NOT_PAID)

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
    request_data['channel_code'] = ADCB_CLIENT_CODE
    return request_data


def get_adcb_verify_redirect_url(response_data, transaction_obj): # partial redemption
    if (response_data.get("results", {}).get("payment_status") and
            response_data.get("results", {}).get("redemption_status")):
        logger.info("Partial payment through card and touchpoints for id "
                    "{}".format(transaction_obj.transaction_id))
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id)
    elif (response_data.get("results", {}).get("payment_status") and not
    response_data.get("results", {}).get("redemption_status")):
        logger.info("Full amount paid through card for id {}".format(
            transaction_obj.transaction_id))
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id)
    elif ("results" not in response_data and
          response_data.get("code") == ADCB_CHECKOUTPG_PAYMENT_NOT_PAID):
        logger.info(
            "Transaction failed at checkout for transaction id {}, failure "
            "url {}".format(transaction_obj.transaction_id,
                            transaction_obj.failure_url))
        response_data["is_redirect"] = False
        redirect_url = None
        return get_adcb_response_url(redirect_url,
                                     transaction_obj.transaction_id)
    else:
        logger.info("Transaction failed for transaction id {}, failure url "
                    "{}".format(transaction_obj.transaction_id,
                                transaction_obj.failure_url))
        return get_adcb_response_url(
            transaction_obj.failure_url, transaction_obj.transaction_id)


def get_adcb_redemption_redirect_url(response_data, transaction_obj): #full redemption
    if response_data.get('results', {}).get('redemption_status'):
        return get_adcb_response_url(
            transaction_obj.success_url, transaction_obj.transaction_id)
    else:
        return get_adcb_response_url(
            transaction_obj.failure_url, transaction_obj.transaction_id)


def get_adcb_response_url(url, transaction_id):
    if url:
        return_url = url + '?transaction_id=' + str(transaction_id)
    else:
        return_url = None
    return return_url
