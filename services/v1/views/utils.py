import json
import logging

from django.db.models import Q

from core.constants import (PURCHASE_PLATFORM_ANDROID, PURCHASE_PLATFORM_IOS,
                            PAYBACK_ACTION_EARN, FORMAT_PARTIAL_PAYMENTS)
from core.core_serializers import PaymentConfigurationSerializer
from core.exceptions import PaymentConfigurationFailed
from core.messages import PAYMENT_REQUEST_KEYS_ERROR
from core.models import Country, PaymentMethodConfig
from core.utils import get_cached_payment_method_config
from integrations.constants import (
    CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE, TABBYPG_HUB_CODE,
    QITAF_HUB_CODE, AMAZONPG_HUB_CODE, HAPPYCREDITS_HUB_CODE
)
from payments.constants import (PAYMENT_STATUS_INITIATED,
                                LANGUAGE_CODE_EN,
                                LANGUAGE_CODE_AR,
                                PAYMENT_OPTION_CHECKOUT_CARD,
                                PAYMENT_OPTION_CHECKOUT_SAVED_CARD,
                                PAYMENT_OPTION_CHECKOUT_APPLEPAY,
                                PAYMENT_OPTION_AMAZON_CARD,
                                PAYMENT_OPTION_AMAZON_SAVED_CARD,
                                PAYMENT_OPTION_AMAZON_APPLEPAY,
                                PAYMENT_METHOD_CARD,
                                PAYMENT_METHOD_SAVED_CARD,
                                PAYMENT_METHOD_APPLEPAY, PAYMENT_METHOD_ADCB,
                                PAYMENT_METHOD_CITI, PAYMENT_METHOD_TABBYPG,
                                PAYMENT_OPTION_TABBYPG, PAYMENT_OPTION_ADCB,
                                PAYMENT_OPTION_CITI_REWARDS,
                                PAYMENT_METHOD_QITAF, PAYMENT_OPTION_QITAF,
                                PAYMENT_METHOD_HAPPY_CREDITS,
                                PAYMENT_OPTION_HAPPY_CREDITS,
                                PAYMENT_METHOD_PAYPAL, PAYMENT_OPTION_PAYPAL,
                                PAYMENT_METHOD_NEQATY, PAYMENT_METHOD_MOKAFA)
from payments.models import Announcement
from services.constants import (YOUPAY_SESSION_KEY, TABBYPG_STORE_CURRENCIES,
                                ADCBPG_STORE_CURRENCIES,
                                AMAZONPG_STORE_CURRENCIES,
                                QITAF_STORE_CURRENCIES, CITI_STORE_CURRENCIES)
from services.models import APIClient

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
        data['amount_in_aed'] = order.get('amount_in_aed')
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
        data['is_guest'] = customer.get('is_guest', False)

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
        session_id = None

    return session_id


def get_payment_options(transaction_obj, gateways):
    """
    used to get gateways from payment gateway serializer
    """

    response_payment_options = {}
    store_currency = transaction_obj.cart_currency
    platform = transaction_obj.platform
    is_guest = transaction_obj.is_guest

    for gateway in gateways:
        code = gateway.code

        response_payment_options = get_checkoutpg_payment_options(
            code, gateway, is_guest, response_payment_options)

        response_payment_options = get_b2cpayback_payment_options(
            code, gateway, store_currency, response_payment_options,
            transaction_obj=transaction_obj)

        response_payment_options = get_tabbypg_payment_options(
            code, store_currency, response_payment_options)

        response_payment_options = get_amazonpg_payment_options(
            code, store_currency, response_payment_options)

        response_payment_options = get_haapycredits_payment_options(
            code, response_payment_options, platform
        )

    return response_payment_options


def get_checkoutpg_payment_options(code, gateway, is_guest,
                                   response_payment_options):
    if code == CHECKOUTPG_HUB_CODE:
        validation_json = gateway.validation_json

        if validation_json:
            paypal_flag = gateway.validation_json.get("is_paypal_enabled",
                                                      False)
            applepay_flag = gateway.validation_json.get(
                "is_applepay_enabled", False)
            saved_card_flag = gateway.validation_json.get(
                "is_saved_card_enabled", False)

            if is_guest:
                saved_card_flag = False

            # enable or disable based on validation_json
            response_payment_options['saved_card'] = saved_card_flag
            response_payment_options['applepay'] = applepay_flag
            response_payment_options['paypal'] = paypal_flag
        else:
            logger.error("validation_json not setup for {}".format(
                gateway.gateway_name))

        # Always active if checkout is active in API client
        response_payment_options['checkoutpg'] = True
    return response_payment_options


def get_b2cpayback_payment_options(code, gateway, store_currency,
                                   response_payment_options, **kwargs):
    transaction_obj = kwargs.get('transaction_obj')
    if code == B2CPAYBACK_HUB_CODE:
        """This will check only B2CPayback gateway"""
        response_payment_options['adcb'] = False
        response_payment_options['citi_rewards'] = False

        if store_currency in ADCBPG_STORE_CURRENCIES:
            response_payment_options['adcb'] = True

        validation_json = gateway.validation_json

        if validation_json:
            is_citi_rewards_enabled = validation_json.get(
                "is_citi_rewards_enabled", False)
            is_qitaf_enabled = validation_json.get("is_qitaf_enabled", False)

            (response_payment_options['qitaf'],
             response_payment_options['citi_rewards']) = (False, False)

            if store_currency in QITAF_STORE_CURRENCIES and is_qitaf_enabled:
                response_payment_options['qitaf'] = True

            if store_currency in CITI_STORE_CURRENCIES and is_citi_rewards_enabled:
                response_payment_options['citi_rewards'] = True
        else:
            logger.error("validation_json not setup for {}".format(
                gateway.gateway_name))
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


def get_haapycredits_payment_options(code, response_payment_options,
                                     platform):
    # happycredits is active only for Android and IOS Platforms
    response_payment_options['happy_credits'] = False

    if platform in [PURCHASE_PLATFORM_ANDROID, PURCHASE_PLATFORM_IOS]:
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


def get_country_for_configuration(transaction):
    try:
        country = Country.objects.get(iso_code=transaction.country_code)
    except Exception as e:
        logger.error("Country not found for transaction {}".format(
            transaction.transaction_id))
        country = None
    return country


def get_client_for_configuration(transaction):
    try:
        client = APIClient.objects.get(id=transaction.api_client_id)
    except Exception as e:
        logger.error("Client not found for transaction {}".format(
            transaction.transaction_id))
        client = None
    return client


def get_payment_methods(transaction, client, country):
    logger.info("Getting payment methods for transaction {}".format(
        transaction.transaction_id))

    platform = transaction.platform

    try:
        payment_method_query = Q(payment_method__active=True, client=client,
                                 country=country, active=True)
        if transaction.is_guest:
            payment_method_query = Q(payment_method__active=True,
                                     client=client,
                                     country=country, active=True,
                                     guest_user_enabled=True)

        payment_method_config_qs = get_cached_payment_method_config()
        payment_method_configs = payment_method_config_qs.filter(
            payment_method_query)

        payment_options = {}
        payment_config_data = {}

        for config in payment_method_configs:
            payment_option_key = get_payment_option_constant(
                config.payment_method.payment_gateway,
                config.payment_method.payment_method
            )
            payment_options[payment_option_key] = True

            payment_config_data[
                payment_option_key] = PaymentConfigurationSerializer(
                config.payment_method).data

        if payment_options.get('happy_credits') is not None:
            if platform not in [PURCHASE_PLATFORM_ANDROID,
                                PURCHASE_PLATFORM_IOS]:
                payment_options['happy_credits'] = False

    except Exception as e:
        payment_options = None
        payment_config_data = None
        logger.error(
            "Error occurred while getting payment options for "
            "transaction, {}, {}".format(transaction.transaction_id, str(e)),
            exc_info=True)
    return payment_options, payment_config_data


def get_payment_option_constant(payment_gateway, payment_method):
    payment_gateway_value = payment_gateway.code
    payment_method_lower = payment_method.lower()

    payment_option_mapping = {

        (CHECKOUTPG_HUB_CODE,
         PAYMENT_METHOD_CARD): PAYMENT_OPTION_CHECKOUT_CARD,
        (CHECKOUTPG_HUB_CODE,
         PAYMENT_METHOD_SAVED_CARD): PAYMENT_OPTION_CHECKOUT_SAVED_CARD,
        (CHECKOUTPG_HUB_CODE,
         PAYMENT_METHOD_APPLEPAY): PAYMENT_OPTION_CHECKOUT_APPLEPAY,
        (CHECKOUTPG_HUB_CODE,
         PAYMENT_METHOD_PAYPAL): PAYMENT_OPTION_PAYPAL,

        (AMAZONPG_HUB_CODE, PAYMENT_METHOD_CARD): PAYMENT_OPTION_AMAZON_CARD,
        (AMAZONPG_HUB_CODE,
         PAYMENT_METHOD_SAVED_CARD): PAYMENT_OPTION_AMAZON_SAVED_CARD,
        (AMAZONPG_HUB_CODE,
         PAYMENT_METHOD_APPLEPAY): PAYMENT_OPTION_AMAZON_APPLEPAY,

        (B2CPAYBACK_HUB_CODE,
         PAYMENT_METHOD_ADCB): PAYMENT_OPTION_ADCB,
        (B2CPAYBACK_HUB_CODE,
         PAYMENT_METHOD_CITI): PAYMENT_OPTION_CITI_REWARDS,
        (B2CPAYBACK_HUB_CODE,
         PAYMENT_METHOD_QITAF): PAYMENT_OPTION_QITAF,
        (B2CPAYBACK_HUB_CODE,
         PAYMENT_METHOD_NEQATY): PAYMENT_METHOD_NEQATY,
        (B2CPAYBACK_HUB_CODE,
         PAYMENT_METHOD_MOKAFA): PAYMENT_METHOD_MOKAFA,

        (TABBYPG_HUB_CODE,
         PAYMENT_METHOD_TABBYPG): PAYMENT_OPTION_TABBYPG,

        (HAPPYCREDITS_HUB_CODE,
         PAYMENT_METHOD_HAPPY_CREDITS): PAYMENT_OPTION_HAPPY_CREDITS,
    }

    constant = payment_option_mapping.get(
        (payment_gateway_value, payment_method_lower), None)

    return constant


def payment_configuration_check(**kwargs):
    payment_options = None,
    payment_config_data = None
    transaction_id = None
    payment_method = None

    transaction_obj = kwargs.get('transaction_obj', None)
    payment_method = kwargs.get('payment_method', None)
    payback_action = kwargs.get('payback_action', None)

    client = transaction_obj.api_client.id
    country = get_country_for_configuration(transaction_obj)
    transaction_id = transaction_obj.transaction_id

    payment_options, payment_config_data = get_payment_methods(
        transaction_obj, client, country)

    if payback_action == PAYBACK_ACTION_EARN:
        if payment_method not in payment_config_data:
            raise PaymentConfigurationFailed(
                "PaymentConfiguration for {} is not active or unavailable for "
                "transaction {}".format(payment_method, transaction_id))

        payment_config_datum = payment_config_data[payment_method]

        if payment_config_datum.get('earn_enabled') is False:
            raise PaymentConfigurationFailed(
                "Earn not enabled for PaymentConfiguration {} for "
                "transaction {}".format(payment_method, transaction_id))

        if transaction_obj.payment_method == FORMAT_PARTIAL_PAYMENTS.format(
                payment_method) and payment_config_datum.get(
            'earn_on_partial_redemption') is False:

            raise PaymentConfigurationFailed(
                "Earn on partial redemption for PaymentConfiguration {} for "
                "transaction {}".format(payment_method, transaction_id))

    return payment_options, payment_config_data
