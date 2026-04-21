import json
import logging

from django.core.cache import cache
from django.db.models import Q

from core.constants import (PURCHASE_PLATFORM_ANDROID, PURCHASE_PLATFORM_IOS,
                            PAYBACK_ACTION_EARN, FORMAT_PARTIAL_PAYMENTS,
                            BETA_USER_ENABLED, BETA_USER_ONLY_EARN,
                            BETA_USER_ONLY_BURN, REWARDS_ORDER_PREFIXES,
                            REWARDS_ORDER_TAGS, REWARDS_TOP_UP_ORDER_PREFIX)
from core.core_serializers import PaymentConfigurationSerializer
from core.exceptions import PaymentConfigurationFailed
from core.messages import PAYMENT_REQUEST_KEYS_ERROR
from core.models import Country, BetaUser
from core.utils import (get_cached_payment_method_config,
                        get_configuration_data,
                        get_gateway_additional_fee)
from integrations.constants import (
    CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE, TABBYPG_HUB_CODE,
    AMAZONPG_HUB_CODE, HAPPYCREDITS_HUB_CODE, PAYPAL_HUB_CODE,
    ADDITIONAL_AMEX_CARD_FEE
)
from integrations.models import PaymentGateway
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
                                PAYMENT_METHOD_NEQATY, PAYMENT_METHOD_MOKAFAA,
                                PAYMENT_METHOD_ANB, PAYMENT_OPTION_ANB,
                                PAYMENT_OPTION_CHECKOUT_PAYPAL)
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

    order = data.get('order', {})
    payment = data.get('payment')
    customer = data.get('customer', {})
    urls = data.get('urls')
    order_history = data.get('order_history')
    order_items = data.get('order_items')
    data['redemption_partner'] = data.get('redemption_partner')
    udf1 = data.get('udf1')
    corporate_id = customer.get('corporate_id')
    additional_charges = order.get('additional_charges')
    cart_additional_charges = order.get('cart_additional_charges')
    if isinstance(udf1, dict):
        udf1.update({
            'corporate_id': corporate_id,
            'additional_charges': additional_charges,
            'cart_additional_charges': cart_additional_charges
        })
        data['udf1'] = udf1
    else:
        data['udf1'] = {
            'corporate_id': corporate_id,
            'additional_charges': additional_charges,
            'cart_additional_charges': cart_additional_charges
        }

    if order and payment and customer and urls:
        data['amount'] = order.get('amount')
        data['amount_in_aed'] = order.get('amount_in_aed')
        data['service_fee'] = order.get('service_fee')
        data['base_amount'] = order.get('base_amount')
        data['VAT_amount'] = order.get('VAT_amount')
        data['currency'] = order.get('currency')
        data['country_code'] = order.get('country_code')
        data['platform_fee'] = order.get('platform_fee')

        data['cart_amount'] = order.get('cart_amount')
        data['cart_currency'] = order.get('cart_currency')
        data['cart_service_fee'] = order.get('cart_service_fee')
        data['cart_base_amount'] = order.get('cart_base_amount')
        data['cart_VAT_amount'] = order.get('cart_VAT_amount')
        data['additional_vat_percentage'] = order.get(
            'additional_vat_percentage')
        data['additional_currency_decimal_notation'] = (
            order.get('additional_currency_decimal_notation'))
        data['order_id'] = order.get('order_id')
        data['is_offer_applicable'] = order.get('is_offer_applicable', False)
        data['cart_platform_fee'] = order.get('cart_platform_fee')

        data['invoice_id'] = payment.get('invoice_id')
        data['order_reference'] = payment.get('order_reference')
        data['language'] = payment.get('language')
        data['platform'] = payment.get('payment_platform')
        data['ip'] = payment.get('ip')
        data['loyalty_level'] = payment.get('loyalty_level')

        data['customer_email'] = customer.get('email')
        data['customer_phone'] = customer.get('phone')
        data['customer_name'] = customer.get('name')
        data['customer_uid'] = customer.get('customer_uid')
        data['is_guest'] = customer.get('is_guest', False)

        data['success_url'] = urls.get('success_url')
        data['failure_url'] = urls.get('failure_url')
        data['cancel_url'] = urls.get('cancel_url')
        data['verify_url'] = urls.get('verify_url')

        data['payment_status'] = PAYMENT_STATUS_INITIATED

        data['order_items'] = order_items
        data['order_history'] = order_history
        purchase_origin = order.get('purchase_origin', None)
        if purchase_origin:
            data['clevertap_items'] = {
                'purchase_origin': purchase_origin
            }

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
    payment_gateways = PaymentGateway.objects.filter(is_active=True)
    announcements = Announcement.objects.filter(
        gateway__in=payment_gateways,
        platform=platform,
        is_active=True,
        payment_option__isnull=False
    ).values(
        'gateway__code',
        'payment_option__payment_method',
        'offer_message',
        'offer_message_arabic'
    ).distinct()

    announcements_dict = {}

    for ann in announcements:
        pg_code = ann['gateway__code']
        method = ann['payment_option__payment_method']

        announcement = {
            LANGUAGE_CODE_EN: ann['offer_message'],
            LANGUAGE_CODE_AR: ann['offer_message_arabic']
        }

        if pg_code not in announcements_dict:
            announcements_dict[pg_code] = {}

        announcements_dict[pg_code][method] = announcement

    return announcements_dict


def get_payment_options_announcements(announcement_objs):
    options_values_dict = announcement_objs.exclude(
        payment_option=None).values(
        'payment_option__payment_method', 'offer_message',
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


def get_second_project_configuration_data(gateway, transaction_obj):
    cache_key = f"payment_config_{gateway.code}"
    payment_method_config = cache.get(cache_key)
    if not payment_method_config:
        payment_method_config = get_configuration_data(gateway.code,
                                                       transaction_obj,
                                                       gateway)
        cache.set(cache_key, payment_method_config, timeout=180)

    return payment_method_config


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
            payment_method_query &= Q(guest_user_enabled=True)
        if transaction.redemption_partner:
            payment_method_query &= Q(
                payment_method__payment_method=transaction.redemption_partner)

        payment_method_config_qs = get_cached_payment_method_config()
        payment_method_configs = payment_method_config_qs.filter(
            payment_method_query)

        payment_options = {}
        payment_config_map = {}

        for config in payment_method_configs:
            method = config.payment_method
            method_key = method.payment_method
            try:
                method_config = PaymentConfigurationSerializer(method).data
                if method.payment_gateway.code == CHECKOUTPG_HUB_CODE and method_key in [
                    PAYMENT_OPTION_CHECKOUT_CARD,
                    PAYMENT_OPTION_CHECKOUT_SAVED_CARD,
                ]:
                    if "checkoutpg_config" not in payment_config_map:
                        logger.info(
                            "Loading checkoutpg_config for transaction_id=%s",
                            transaction.transaction_id)
                        checkout_obj = get_configuration_data(
                            CHECKOUTPG_HUB_CODE, transaction)
                        payment_config_map[
                            "checkoutpg_config"] = checkout_obj.response_data
                        additional_fee_obj = get_gateway_additional_fee(
                            transaction.currency, ADDITIONAL_AMEX_CARD_FEE,
                            CHECKOUTPG_HUB_CODE, "checkout_card")
                        additional_fee_config = (
                            get_checkout_amex_additional_fee(
                                additional_fee_obj, transaction))
                        logger.info(
                            "additional_fee for transaction {} amex card "
                            "is {}".format(
                                transaction.transaction_id,
                                additional_fee_config))
                        payment_config_map["checkoutpg_config"][
                            "amex_config"] = additional_fee_config

                else:
                    if method.is_second_project_config_enabled:
                        if method.partial_redemption_allowed:
                            if "checkoutpg_config" not in payment_config_map:
                                logger.info(
                                    "Loading checkoutpg_config for transaction_id=%s",
                                    transaction.transaction_id)
                                checkout_obj = get_configuration_data(
                                    CHECKOUTPG_HUB_CODE, transaction)
                                payment_config_map[
                                    "checkoutpg_config"] = checkout_obj.response_data
                        method_specific_config = method.payment_method_config
                        if not method_specific_config:
                            second_project_obj = get_second_project_configuration_data(
                                method.payment_gateway, transaction)
                            if second_project_obj:
                                results = second_project_obj.response_data.get(
                                    "results", [])
                                method_specific_config = next(
                                    (item for item in results if
                                     item["code"] == method.code), None
                                )
                                if method_specific_config:
                                    method.payment_method_config = method_specific_config
                                    method.save(update_fields=[
                                        "payment_method_config"])

                        if method_specific_config:
                            merged_config = {**method_specific_config,
                                             **method_config}
                            dynamic_key = f"{method_key.lower()}_config"
                            payment_config_map[dynamic_key] = merged_config
                            method_config[
                                dynamic_key] = method_specific_config
                        else:
                            logger.error(
                                "Missing second project configuration for method=%s, transaction_id=%s",
                                method.code,
                                transaction.transaction_id,
                            )
                            continue

                is_enabled = update_payment_method_config(transaction, config,
                                                          payment_config_map,
                                                          method_key)
                payment_options[method_key] = is_enabled
                if (transaction.order_reference.startswith(
                        REWARDS_TOP_UP_ORDER_PREFIX) and any(
                        tag in transaction.order_reference for tag in
                        REWARDS_ORDER_TAGS)):
                    udf1 = getattr(transaction, "udf1", None)
                    if not udf1:
                        continue
                    is_via_payment_link = (
                            isinstance(udf1, dict) and
                            udf1.get("is_via_payment_link") is True
                    )
                    if is_via_payment_link and isinstance(payment_options, dict):
                        payment_options.pop("checkout_saved_card", None)
                        logger.info("Payment link transaction found. "
                                    "Removing checkout_saved_card from "
                                    "payment_options for transaction_id {}"
                                    .format(transaction.transaction_id))

            except Exception as inner_exc:
                logger.error(
                    "Error while processing payment method=%s for transaction_id=%s: %s",
                    method_key,
                    transaction.transaction_id,
                    str(inner_exc),
                    exc_info=True,
                )
                continue

        if payment_options.get('happy_credits') is not None:
            if platform not in [PURCHASE_PLATFORM_ANDROID,
                                PURCHASE_PLATFORM_IOS]:
                payment_options['happy_credits'] = False

    except Exception as e:
        payment_options = None
        payment_config_map = None
        logger.error(
            "Error occurred while getting payment options for "
            "transaction, {}, {}".format(transaction.transaction_id, str(e)),
            exc_info=True)
    return payment_options, payment_config_map


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
         PAYMENT_METHOD_PAYPAL): PAYMENT_OPTION_CHECKOUT_PAYPAL,

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
         PAYMENT_METHOD_MOKAFAA): PAYMENT_METHOD_MOKAFAA,
        (B2CPAYBACK_HUB_CODE, PAYMENT_METHOD_ANB): PAYMENT_OPTION_ANB,

        (TABBYPG_HUB_CODE,
         PAYMENT_METHOD_TABBYPG): PAYMENT_OPTION_TABBYPG,

        (HAPPYCREDITS_HUB_CODE,
         PAYMENT_METHOD_HAPPY_CREDITS): PAYMENT_OPTION_HAPPY_CREDITS,

        (PAYPAL_HUB_CODE,
         PAYMENT_METHOD_PAYPAL): PAYMENT_OPTION_PAYPAL,
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

    payment_config_key = payment_method + "_config"

    if payback_action == PAYBACK_ACTION_EARN:
        if payment_config_key not in payment_config_data:
            raise PaymentConfigurationFailed(
                "PaymentConfiguration for {} is not active or unavailable for "
                "transaction {}".format(payment_method, transaction_id))

        payment_config_datum = payment_config_data[payment_config_key]

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


def update_payment_method_config(transaction, config, payment_config_data,
                                 payment_option_key):
    """
    Adjust the payment configuration based on beta version and payment gateway code.
    """
    is_enabled = True
    if config.payment_method.beta_version == BETA_USER_ENABLED:
        is_enabled = check_is_user_beta_enabled(transaction)

    if config.payment_method.payment_gateway.code == B2CPAYBACK_HUB_CODE:

        if config.payment_method.beta_version == BETA_USER_ONLY_EARN:
            is_beta_user = check_is_user_beta_enabled(transaction)
            if not is_beta_user:
                payment_config_data[payment_option_key][
                    'earn_enabled'] = False
                payment_config_data[payment_option_key][
                    'earn_on_partial_redemption'] = False

        if config.payment_method.beta_version == BETA_USER_ONLY_BURN:
            is_beta_user = check_is_user_beta_enabled(transaction)
            if not is_beta_user:
                payment_config_data[payment_option_key][
                    'burn_full_redemption_enabled'] = False
                payment_config_data[payment_option_key][
                    'partial_redemption_allowed'] = False

    return is_enabled


def check_is_user_beta_enabled(transaction):
    """
    Checks if the customer associated with the given transaction is a beta user.
    Args:
        transaction: The transaction object containing customer email.
    Returns:
        bool: True if the customer is an active beta user, False otherwise.
    """
    try:
        customer_email = transaction.customer_email
        beta_user = BetaUser.objects.get(beta_user_email=customer_email)
        return True if beta_user else False
    except BetaUser.DoesNotExist:
        return False


def is_rewards_order_reference(order_reference):
    """
    Checks if the given order reference is a rewards order reference.

    Args:
        order_reference (str): The order reference of the transaction object.

    Returns:
        bool: True if the order reference starts with 'TOP' or 'PMT' and
        contains '|REW|', False otherwise.
    """
    if order_reference is None:
        return False
    return (any(order_reference.startswith(prefix) for
                    prefix in REWARDS_ORDER_PREFIXES) and any(
                tag in order_reference for tag in REWARDS_ORDER_TAGS))


def process_total_quantity_eligibility(transaction, response_data):
    """
    Processes total quantity eligibility for a transaction.

    Args:
        transaction: The transaction object containing udf1 and transaction_id
        response_data: The response dictionary to update with total_quantity

    Returns:
        response_data: The updated response dictionary with total_quantity
        if eligible
    """
    udf1 = getattr(transaction, "udf1", None)
    if not udf1 or not isinstance(udf1, dict):
        return response_data

    order_quantity = udf1.get("order_quantity")
    if order_quantity is not None:
        logger.info("Total quantity eligibility is true for "
                    "transaction {} and total quantity is {}"
                    .format(transaction.transaction_id, order_quantity))
        response_data["data"]["total_quantity"] = order_quantity

    return response_data

def get_checkout_amex_additional_fee(additional_fee_obj, transaction_obj):
    """
    Calculates the additional fee for Amex card based on the percentage and VAT configured.
    :param additional_fee_obj:
    :param transaction_obj:
    :return: config dict with additional fee and total amount details
    """
    amex_additional_fee_config = {}
    if additional_fee_obj and additional_fee_obj.percentage:
        additional_fee = round(
            transaction_obj.base_amount * (additional_fee_obj.percentage / 100), 2)
        logger.info(
            "Additional fee for Amex card for transaction {} is {}".format(
                transaction_obj.transaction_id, additional_fee))
        additional_fee_vat = round(additional_fee * (
                additional_fee_obj.VAT_percentage / 100), 2)
        total_vat = round(transaction_obj.VAT_amount + additional_fee_vat, 2)
        giftee_fee = round((transaction_obj.udf1 or {}).get(
            "additional_charges") or 0, 2)
        total_amount = round(
            transaction_obj.base_amount + transaction_obj.service_fee +
            additional_fee + giftee_fee + total_vat, 2)
        amex_additional_fee_config = {
            "additional_fee": str(additional_fee),
            "additional_fee_vat": str(additional_fee_vat),
            "combined_vat_amount": str(total_vat),
            "total_amount": str(total_amount),
            "processing_fee_percentage": str(additional_fee_obj.percentage),
            "processing_fee_vat_percentage": str(
                additional_fee_obj.VAT_percentage)
        }
        logger.info(
            "amex_additional_fee_config for transaction {} is {}".format(
                transaction_obj.transaction_id, amex_additional_fee_config))
    else:
        logger.info(
            "No additional fee configured for Amex card for transaction "
            "{}".format(transaction_obj.transaction_id))
    return amex_additional_fee_config
