import json
import logging

from core.messages import PAYMENT_REQUEST_KEYS_ERROR
from integrations.constants import (
    CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE, TABBYPG_HUB_CODE, QITAF_HUB_CODE
)
from payments.constants import PAYMENT_STATUS_INITIATED
from payments.models import Announcement
from services.constants import YOUPAY_SESSION_KEY
from services.v1.constants import PAYMENT_OPTIONS

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
    order_history = data.get('order_history')
    order_items = data.get('order_items')

    if order and payment and customer and urls:
        data['amount'] = order.get('amount')
        data['service_fee'] = order.get('service_fee')
        data['base_amount'] = order.get('base_amount')
        data['VAT_amount'] = order.get('VAT_amount')
        data['currency'] = order.get('currency')

        data['cart_amount'] = order.get('cart_amount')
        data['cart_currency'] = order.get('cart_currency')
        data['cart_service_fee'] = order.get('cart_service_fee')
        data['cart_base_amount'] = order.get('cart_base_amount')
        data['cart_VAT_amount'] = order.get('cart_VAT_amount')

        data['invoice_id'] = payment.get('invoice_id')
        data['order_reference'] = payment.get('order_reference')
        data['language'] = payment.get('language')
        data['platform'] = payment.get('payment_platform')
        data['ip'] = payment.get('ip')
        data['loyalty_level'] = payment.get('loyalty_level')

        data['customer_email'] = customer.get('email')
        data['customer_phone'] = customer.get('phone')
        data['customer_name'] = customer.get('name')

        data['success_url'] = urls.get('success_url')
        data['failure_url'] = urls.get('failure_url')
        data['cancel_url'] = urls.get('cancel_url')
        data['verify_url'] = urls.get('verify_url')

        data['payment_status'] = PAYMENT_STATUS_INITIATED

        data['order_items'] = order_items
        data['order_history'] = order_history

        return data
    else:
        logger.error(PAYMENT_REQUEST_KEYS_ERROR)
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


def get_session_id_from_header(request):
    """
    used to get session_id request

    take session_id from request session
    """
    session_key = YOUPAY_SESSION_KEY
    logger.info("Cookies keys: %s", request.COOKIES.keys())

    logger.info("Header data is {} ".format(request.headers))

    try:
        session_id = request.session[session_key]
        logger.info("Session data is {} and session_id: {}"
                    "".format(request.session, session_id))
    except Exception as e:
        logger.info(
            "Couldnt able to load Session keys {} ".format(
                request.session.keys()))
        logger.error(
            "Error while getting session_id from request: {}".format(e))
        session_id = None

    return session_id


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
