import json
import logging

from core.messages import PAYMENT_REQUEST_KEYS_ERROR
from integrations.constants import (
    CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE, TABBYPG_HUB_CODE,
    QITAF_HUB_CODE, AMAZONPG_HUB_CODE, HAPPYCREDITS_HUB_CODE
)
from payments.constants import PAYMENT_STATUS_INITIATED, LANGUAGE_CODE_EN, \
    LANGUAGE_CODE_AR
from payments.models import Announcement
from services.constants import (YOUPAY_SESSION_KEY, TABBYPG_STORE_CURRENCIES,
                                ADCBPG_STORE_CURRENCIES,
                                AMAZONPG_STORE_CURRENCIES)

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
        data['country_code'] = order.get('country_code')

        data['cart_amount'] = order.get('cart_amount')
        data['cart_currency'] = order.get('cart_currency')
        data['cart_service_fee'] = order.get('cart_service_fee')
        data['cart_base_amount'] = order.get('cart_base_amount')
        data['cart_VAT_amount'] = order.get('cart_VAT_amount')
        data['additional_vat_percentage'] = order.get(
            'additional_vat_percentage')
        data['additional_currency_decimal_notation'] = (
            order.get('additional_currency_decimal_notation'))

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


def get_payment_options(transaction_obj, gateways):
    """
    used to get gateways from payment gateway serializer
    """

    response_payment_options = {}
    store_currency = transaction_obj.cart_currency
    for gateway in gateways:
        code = gateway.code

        response_payment_options = get_checkoutpg_payment_options(
            code, gateway, response_payment_options)

        response_payment_options = get_b2cpayback_payment_options(
            code, store_currency, response_payment_options)

        response_payment_options = get_tabbypg_payment_options(
            code, store_currency, response_payment_options)

        response_payment_options = get_amazonpg_payment_options(
            code, store_currency, response_payment_options)

        response_payment_options = get_haapycredits_payment_options(
            code, response_payment_options
        )

    return response_payment_options


def get_checkoutpg_payment_options(code, gateway, response_payment_options):
    if code == CHECKOUTPG_HUB_CODE:
        validation_json = gateway.validation_json

        if validation_json:
            paypal_flag = gateway.validation_json.get("is_paypal_enabled",
                                                      False)
            applepay_flag = gateway.validation_json.get(
                "is_applepay_enabled", False)
            saved_card_flag = gateway.validation_json.get(
                "is_saved_card_enabled", False)

            # enable or disable based on validation_json
            response_payment_options['saved_card'] = saved_card_flag
            response_payment_options['applepay'] = applepay_flag
            response_payment_options['paypal'] = paypal_flag
        else:
            logger.warning("validation_json not setup for {}".format(
                gateway.gateway_name))

        # Always active if checkout is active in API client
        response_payment_options['checkoutpg'] = True
    return response_payment_options


def get_b2cpayback_payment_options(code, store_currency,
                                   response_payment_options):
    if code == B2CPAYBACK_HUB_CODE and (store_currency in
                                        ADCBPG_STORE_CURRENCIES):
        response_payment_options['adcb'] = True
    return response_payment_options


def get_tabbypg_payment_options(code, store_currency,
                                response_payment_options):
    if code == TABBYPG_HUB_CODE and (store_currency in
                                     TABBYPG_STORE_CURRENCIES):
        response_payment_options['tabbypg'] = True
    return response_payment_options


def get_amazonpg_payment_options(code, store_currency,
                                 response_payment_options):
    if code == AMAZONPG_HUB_CODE and (store_currency in
                                      AMAZONPG_STORE_CURRENCIES):
        response_payment_options['amazonpg'] = True
    return response_payment_options


def get_haapycredits_payment_options(code, response_payment_options):
    if code == HAPPYCREDITS_HUB_CODE:
        response_payment_options['happy_credits'] = True

    return response_payment_options


def get_announcements(platform):
    """
    used to fetch the active announcements for payment gateways
    """
    pg_list = [CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE,
               TABBYPG_HUB_CODE, QITAF_HUB_CODE]
    payment_options_announcements_dict = {}
    announcements_dict = {}
    for pg in pg_list:
        announcement_objs = Announcement.objects.filter(
            gateway__code=pg, platform=platform, is_active=True)
        payment_options_announcements = get_payment_options_announcements(
            announcement_objs)
        for payment_options_dict in payment_options_announcements:
            payment_options_announcements_dict[payment_options_dict.get(
                'payment_option__name')] = {
                LANGUAGE_CODE_EN: payment_options_dict.get(
                    'offer_message'),
                LANGUAGE_CODE_AR: payment_options_dict.get(
                    'offer_message_arabic')}
        for obj in announcement_objs:
            if obj.gateway.code == B2CPAYBACK_HUB_CODE:
                announcements_dict['b2cpayback'] = {
                    LANGUAGE_CODE_EN: obj.offer_message,
                    LANGUAGE_CODE_AR: obj.offer_message_arabic
                }
            elif obj.gateway.code == TABBYPG_HUB_CODE:
                announcements_dict['tabbypg'] = {
                    LANGUAGE_CODE_EN: obj.offer_message,
                    LANGUAGE_CODE_AR: obj.offer_message_arabic
                }
            elif obj.gateway.code == QITAF_HUB_CODE:
                announcements_dict['qitafpg'] = {
                    LANGUAGE_CODE_EN: obj.offer_message,
                    LANGUAGE_CODE_AR: obj.offer_message_arabic
                }
            elif obj.gateway.code == AMAZONPG_HUB_CODE:
                announcements_dict['amazonpg'] = {
                    LANGUAGE_CODE_EN: obj.offer_message,
                    LANGUAGE_CODE_AR: obj.offer_message_arabic
                }
    announcements_dict['checkoutpg'] = payment_options_announcements_dict
    return announcements_dict


def get_payment_options_announcements(announcement_objs):
    options_values_dict = announcement_objs.exclude(
        payment_option=None).values(
        'payment_option__name', 'offer_message',
        'offer_message_arabic').distinct()
    return options_values_dict
