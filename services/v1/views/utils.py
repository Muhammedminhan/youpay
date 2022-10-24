import json
import logging
import requests

from django.conf import settings
from services.v1.constants import (
    PAYMENT_OPTIONS, B2C_PAYBACK_YOUPAY_PRODUCT_CODE)
from integrations.constants import (
    CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE, TABBYPG_HUB_CODE, QITAF_HUB_CODE
)
from payments.constants import PAYMENT_STATUS_INITIATED
from payments.models import Announcement

logger = logging.getLogger(__name__)


def reformat_payment_request_data(data):
    """
    used to reformat payment request data, so that we can create payment with
    serializer easily, ie data in object format to individual key value pairs
    """
    data['request_data'] = json.loads(json.dumps(data))

    order = data.get('order')
    payment = data.get('payment')
    customer = data.get('customer')
    urls = data.get('urls')

    if order and payment and customer:
        data['amount'] = order.get('amount')
        data['service_fee'] = order.get('service_fee')
        data['base_amount'] = order.get('base_amount')
        data['VAT_amount'] = order.get('VAT_amount')
        data['currency'] = order.get('currency')

        data['invoice_id'] = payment.get('invoice_id')
        data['order_reference'] = payment.get('order_reference')
        data['language'] = payment.get('language')
        data['platform'] = payment.get('payment_platform')
        data['ip'] = payment.get('ip')

        data['customer_email'] = customer.get('email')
        data['customer_phone'] = customer.get('phone')
        data['customer_name'] = customer.get('name')

        data['success_url'] = urls.get('success_url')
        data['failure_url'] = urls.get('failure_url')
        data['cancel_url'] = urls.get('cancel_url')
        data['verify_url'] = urls.get('verify_url')

        data['payment_status'] = PAYMENT_STATUS_INITIATED
        return data
    else:
        logger.error(
            "payment request data is not in proper format, one of the data is"
            "missing ie order or payment or customer")
        return None


def get_data_from_request(fields, request_data):
    """
    used to get data from request
    """
    data = {}
    for field in fields:
        data[field] = request_data.get(field)
    data['request_data'] = request_data
    return data


def get_session_id_and_transaction_id(id):
    """
    used to get session_id and transaction_id from id
    syntax : "session_id-transaction_id"
    example : "SESSION_ID-5717e1f3-727d-4bc5-8055-b65ea096b422"
    """
    session_id = id.split('-')[0]
    transaction_id = id.split('-')[1:]
    delimiter = '-'
    return session_id, delimiter.join(transaction_id)


def get_payment_options(payment_gateway_serializer):
    """
    used to get gateways from payment gateway serializer
    """
    response_payment_options = PAYMENT_OPTIONS

    payment_gateways = payment_gateway_serializer.data

    for payment_gateway in payment_gateways:
        code = payment_gateway.get('code')
        if code == CHECKOUTPG_HUB_CODE:
            response_payment_options['checkoutpg'] = True
            response_payment_options['saved_card'] = True
            response_payment_options['applepay'] = True

        if code == B2CPAYBACK_HUB_CODE:
            response_payment_options['adcb'] = True

        if code == TABBYPG_HUB_CODE:
            response_payment_options['tabbypg'] = True

    return response_payment_options


def get_announcements():
    """
    used to fetch the active announcements for payment gateways
    """
    pg_list = [CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE,
               TABBYPG_HUB_CODE, QITAF_HUB_CODE]
    announcements_list = []
    for pg in pg_list:
        announcement_objs = Announcement.objects.filter(gateway__code=pg,
                                                        is_active=True)
        pg_announcements = []
        for obj in announcement_objs:
            pg_announcements.append(obj.offer_message)
        announcements_list.append(pg_announcements)
    announcements_dict = {
        "checkoutpg": announcements_list[0],
        "b2cpayback": announcements_list[1],
        "tabbypg": announcements_list[2],
        "qitafpg": announcements_list[3]
    }
    return announcements_dict


def get_payback_config(transaction):
    product_code = B2C_PAYBACK_YOUPAY_PRODUCT_CODE
    amount = str(transaction.amount)
    currency = str(transaction.currency)
    config_request_data = {
        "amount": amount, "currency": currency,
        "product_code": product_code
    }
    request_data_json = json.dumps(config_request_data)
    url = settings.B2C_PAYBACK_DOMAIN + '/payback/api/v1/configuration/'
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, data=request_data_json,
                             headers=headers)
    except Exception as e:
        response = None
        logger.error("config api call to b2cpayback failed", exc_info=e)
    return response.json()
