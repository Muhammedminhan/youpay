import json
import logging
from base64 import b64decode, b64encode
from contextlib import contextmanager
from decimal import Decimal
from functools import wraps
from os import urandom
from time import sleep

import redis
from Crypto.Cipher import AES
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache

from core.constants import (COMMON_ENCRYPTION_KEY, FERNET_KEY,
                            BROWSER_VALUE_ENCRYPTION_KEY)
from core.messages import (IS_REDIRECT, REDIRECT_URL, TRANSACTION_MSG,
                           IS_SUCCESS)
from core.models import (AppConfig, Currency, PaymentMethodConfig,
                         PaymentConfiguration)
from integrations.constants import (CHECKOUTPG_HUB_CODE, B2CPAYBACK_HUB_CODE,
                                    PAYMENT_METHOD_CONFIG_CACHE_KEY,
                                    PAYMENT_CONFIG_CACHE_KEY)
from integrations.models import PaymentGateway, AdditionalChargeConfiguration
from payments.constants import (
    PAYMENT_STATUS_DECLINED, PAYMENT_STATUS_DECLINED_RETRY,
    PAYMENT_STATUS_PAID, PAYMENT_METHOD_APPLEPAY, PAYMENT_STATUS_REJECTED,
    PAYMENT_STATUS_REJECTED_RETRY, PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING, PAYMENT_SCHEME_MADA)
from services.constants import SOFT_DECLINE_RESPONSE_CODE_STARTSWITH
from services.models import ConfigurationData
from services.v1.views.common import YouPayTransactionCRUD, is_redirect

logger = logging.getLogger(__name__)


def retry(exception_to_ocheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param exception_to_ocheck: the exception to check. may be a tuple of
        exceptions to check
    :type exception_to_ocheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_ocheck as e:
                    msg = "%s, Retrying Webhook..." % (str(e))
                    if logger:
                        logger.warning(msg)
                    else:
                        logger.info(msg)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry

    return deco_retry


def decrypt_payment_data(encrypted_data):
    """
    This method is for decrypt payment data

    input : encrypted_data - dict
    output : decrypted_data - dict
    """
    try:
        b64 = encrypted_data
        json_k = ['nonce', 'ciphertext', 'tag']
        jv = {k: b64decode(b64[k]) for k in json_k}
        cipher = AES.new(COMMON_ENCRYPTION_KEY.encode("utf8"),
                         AES.MODE_GCM,
                         nonce=jv['nonce'])
        plaintext = cipher.decrypt_and_verify(jv['ciphertext'], jv['tag'])
        decrypted_data = json.loads(plaintext.decode("utf8"))
        return decrypted_data
    except (ValueError, KeyError):
        logger.error("request data decryption failed.")
        return None


def encrypt_payment_data(raw):
    """
    This method is to encrypt the request data.

    input data : raw - dict
    output data : encrypted_data - str

    """

    raw_text = json.dumps(raw)
    iv = urandom(12)
    cipher = AES.new(COMMON_ENCRYPTION_KEY.encode("utf8"), AES.MODE_GCM, iv)
    ciphertext, tag = cipher.encrypt_and_digest(raw_text.encode("utf8"))
    json_k = ['nonce', 'ciphertext', 'tag']
    json_v = [b64encode(x).decode('utf-8') for x in
              [cipher.nonce, ciphertext, tag]]
    encrypted_data = json.dumps(dict(zip(json_k, json_v)))
    return encrypted_data


def get_app_config():
    """using low level caching for cache site config"""
    cache_key = 'app_config'
    app_config = cache.get(cache_key, None)
    if app_config is None:
        try:
            app_config = AppConfig.objects.latest('id')
            cache.set(cache_key, app_config)
        except(AppConfig.DoesNotExist, Exception):
            logging.error('No site configuration instance found.')
            return None
    return app_config


def get_checkoutpg_config():
    """using low level caching for cache checkoutpg config"""
    cache_key = 'checkoutpg_config'
    checkoutpg_config = cache.get(cache_key, None)
    if checkoutpg_config is None:
        try:
            checkoutpg_config = PaymentGateway.objects.get(
                code=CHECKOUTPG_HUB_CODE)
            cache.set(cache_key, checkoutpg_config)
        except(PaymentGateway.DoesNotExist, Exception):
            logging.error('No checkoutpg configuration instance found.')
            return None
    return checkoutpg_config


def get_payment_gateway_config(gateway_cache_key, gateway_hub_code):
    """using low level caching for cache gateway config"""
    cache_key = gateway_cache_key
    gateway_config = cache.get(cache_key, None)
    if gateway_config is None:
        try:
            gateway_config = PaymentGateway.objects.get(
                code=gateway_hub_code)
            cache.set(cache_key, gateway_config)
        except(PaymentGateway.DoesNotExist, Exception):
            logging.error('No gateway configuration instance found.')
            return None
    return gateway_config


def get_cached_payment_method_config():
    try:
        cache_key = PAYMENT_METHOD_CONFIG_CACHE_KEY
        payment_method_configs = cache.get(cache_key, None)
        if payment_method_configs is None:
            payment_method_configs = PaymentMethodConfig.objects.all()
            cache.set(cache_key, payment_method_configs)

        return payment_method_configs

    except Exception as e:
        logger.error(
            "Error on getting cached PaymentMethodConfig : {}".format(e))
        return PaymentMethodConfig.objects.none()


def invalidate_cached_payment_method_config():
    try:
        cache_key = PAYMENT_METHOD_CONFIG_CACHE_KEY
        cache.delete(cache_key)
    except Exception as e:
        logger.error(
            "Error on invalidating cached PaymentMethodConfig : {}".format(e))


def get_cached_payment_config():
    try:
        cache_key = PAYMENT_CONFIG_CACHE_KEY
        payment_configs = cache.get(cache_key, None)
        if payment_configs is None:
            payment_configs = PaymentConfiguration.objects.all()
            cache.set(cache_key, payment_configs)

        return payment_configs

    except Exception as e:
        logger.error(
            "Error on getting cached PaymentConfiguration : {}".format(e))
        return PaymentConfiguration.objects.none()


def auto_enable_or_disable_point_collection(query):
    """
    Input Payment Config Query
    Output : True or False
    Objective: to check whether we need to enable earn on partial redemption
    """
    payment_config = get_cached_payment_config()
    if payment_config:
        payment_config_data = payment_config.filter(query)
        if payment_config_data.count():
            payment_config_datum = payment_config_data.first()
            return payment_config_datum.earn_on_partial_redemption
    return False


def decimal_rounded(amount, decimal_notation):
    if not isinstance(amount, Decimal):
        amount = Decimal(amount)
    amount_rounded = Decimal(
        amount.quantize(Decimal(str(decimal_notation))))
    return amount_rounded


def get_gateway_additional_fee(payment_option_name):
    """
    :param payment_option_name
    :return:
    """
    additional_fee = None
    if payment_option_name:
        try:
            additional_fee = AdditionalChargeConfiguration.objects.get(
                payment_option__name=payment_option_name, is_active=True)
        except (AdditionalChargeConfiguration.DoesNotExist, Exception):
            logging.info('No additional fee instance found for '
                         '{}.'.format(payment_option_name))
    return additional_fee


def get_site_domain(request):
    if request.is_secure():
        protocol = 'https://'
    else:
        protocol = 'http://'
    return protocol + request.get_host()


def encrypt_string(clear_text):
    """
    This method is to encrypt the string.

    input data : input_string - str
    output data : encrypted_string - str

    FERNET_KEY which is generated using Fernet.generate_key() method
    """

    try:
        fernet = Fernet(FERNET_KEY)
        encrypted_text = fernet.encrypt(clear_text.encode()).decode("utf-8")
        return encrypted_text
    except Exception as e:
        logger.error("Encryption failed. Error: {}".format(e))
        return None


def decrypt_string(encrypted_text):
    """
    This method is for decrypt string

    input : encrypted_string - str
    output : decrypted_string - str

    FERNET_KEY which is generated using Fernet.generate_key() method
    """
    try:
        fernet = Fernet(FERNET_KEY)
        decrypted_text = fernet.decrypt(encrypted_text).decode()
        return decrypted_text
    except Exception as e:
        logger.error(
            "string decryption failed {}. for {}".format(str(e),
                                                         encrypted_text))
        return None


@contextmanager
def wait_redis_lock(
        lock_name, lock_timeout=settings.WAIT_LOCK_DEFAULT_TIMEOUT,
        wait_duration=settings.WAIT_LOCK_DEFAULT_WAIT_DURATION,
        max_retries=settings.WAIT_LOCK_DEFAULT_MAX_RETRIES):
    """
    Executes code if lock `lock_name` isn't set, else it retries after
    `wait_duration` seconds.
    """
    redis_conn = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT,
        db=settings.REDIS_LOCKS_DB
    )

    retries = 0
    while True:
        value = redis_conn.setnx(lock_name, 1)
        redis_conn.expire(lock_name, lock_timeout)
        if value:
            break
        elif retries < max_retries:
            logger.debug("Lock exists...sleeping.")
            sleep(wait_duration)
            retries += 1
        else:
            raise WaitLockException('Unable to acquire lock.')
    try:
        yield
    finally:
        redis_conn.delete(lock_name)


class WaitLockException(Exception):
    """
    WaitLockException
    If retry limit exceeds the maximum limit
    """
    pass


def get_redirect_url(url, transaction_id):
    """
    Method for return redirect urls
    """
    return url + '?transaction_id=' + transaction_id


def process_checkoutpg_response_verification(**kwargs):
    """
    function to process checkoutpg response verification and update in youpay
    transaction table
    """
    earned_point = None
    earn_reference = None
    points_collected_mobile_number = None
    transaction_id = kwargs.get('transaction_id')
    response_data = kwargs.get('response_data')
    is_pre_auth = kwargs.get('is_pre_auth')
    payment_method = kwargs.get('payment_method')
    payment_gateway = kwargs.get('payment_gateway')
    channel_code = kwargs.get('channel_code')
    response_code = kwargs.get('response_data', {}).get('response_code')
    payment_scheme = get_payment_scheme(response_data)

    reference_from_checkout = response_data.get("reference")

    youpay = YouPayTransactionCRUD()
    youpay_transaction = youpay.get_youpay_transaction_data(
        transaction_id)

    youpay_payment_referance = youpay_transaction.payment_reference

    if ((youpay_payment_referance != reference_from_checkout) and
            youpay_payment_referance):
        '''during pre auth check with checkoutpg, youpay transaction data do
         not contain payment reference'''

        logger.error(
            "Payment Referance mismatch found for transaction id {},"
            " reference id from checkout {}, youpay referance {}"
            "".format(transaction_id, reference_from_checkout,
                      youpay_payment_referance))
        if response_code.startswith(
                SOFT_DECLINE_RESPONSE_CODE_STARTSWITH):
            logger.info(
                "transaction failed for transaction id {}, pre-auth soft "
                "decline response code {}".format(
                    transaction_id, response_code))
        else:
            redirect_url = (youpay_transaction.failure_url +
                        '?transaction_id=' + transaction_id)
            response_data = {
                IS_REDIRECT: True,
                REDIRECT_URL: redirect_url,
                TRANSACTION_MSG: {"response_summary": "Payment Failed"},
                IS_SUCCESS: False
            }

            return False, response_data

    if is_pre_auth:
        response_data = format_pre_auth_payment_response_for_verify(
            response_data)

    logger.info(
        "Verify payment response data for transaction {} --> {}".format(
            transaction_id, response_data))
    response_code = response_data.get('response_code', None)

    is_flagged = response_data.get("is_flagged")

    is_payment_verified = False
    if (response_code is None and
            response_data.get(
                "status").lower() == PAYMENT_STATUS_DECLINED):
        '''
        This allow customer to go back to frontend and able to 
        retry payments
        '''
        payment_status = PAYMENT_STATUS_DECLINED_RETRY
    else:
        source = response_data.get('source', None)

        payment_status, is_payment_verified = checkout_decline_check(
            response_data)
        approved = response_data.get('approved', False)

        if source == PAYMENT_METHOD_APPLEPAY and approved:
            # For Applepay only
            payment_status = PAYMENT_STATUS_PAID
            is_flagged = response_data.get("risk", {}).get("flagged")
            is_payment_verified = True


    youpay_obj = YouPayTransactionCRUD()

    youpay_obj.update_youpay_transaction_data(
        {
            'transaction_id': transaction_id,
            "payment_status": payment_status,
            "payment_reference": reference_from_checkout,
            "approved": response_data.get("approved"),
            "response_summary": response_data.get("response_summary"),
            "card_bin": response_data.get("card_bin"),
            "card_last4": response_data.get("card_last4"),
            'payment_scheme': payment_scheme,
            'is_gcc_card': response_data.get("is_gcc_card"),
            'is_flagged': is_flagged,
            'is_fraud': response_data.get("is_fraud"),
            'card_issuer_country': response_data.get("card_issuer_country"),
            'payment_method': payment_method,
            'payment_gateway': payment_gateway,
            'channel_code': channel_code,
            'is_payment_verified': is_payment_verified
        }
    )
    redirect, response_data = is_redirect(transaction_id, response_data)

    # redirect - boolean, response_data - response data(dict) for frontend
    return redirect, response_data


def checkout_decline_check(response_data):

    response_code = str(response_data.get('response_code', None))

    if str(response_code).startswith(
            SOFT_DECLINE_RESPONSE_CODE_STARTSWITH):
        # this allow retry payments
        payment_status = PAYMENT_STATUS_DECLINED_RETRY
        is_payment_verified = False
    else:
        # this doesnt allow retry payments
        payment_status = response_data.get("status").lower()
        is_payment_verified = True

    return payment_status, is_payment_verified


def tabby_reject_check(response_data):
    payment_status = response_data.get("payment_status")

    if payment_status == PAYMENT_STATUS_REJECTED:
        payment_status = PAYMENT_STATUS_REJECTED_RETRY

    return payment_status


def format_pre_auth_payment_response_for_verify(response_data):
    structured_dict = {
        "status": response_data.get("status"),
        "reference": response_data.get("reference"),
        "approved": response_data.get("approved"),
        "response_code": response_data.get("response_code"),
        "response_summary": response_data.get("response_summary"),
        "payment_status_dict": response_data.get("payment_status_dict"),
        "is_fraud": response_data.get("risk", {}).get("fraud"),
        "is_flagged": response_data.get("risk", {}).get("flagged"),
        "card_bin": response_data.get("source", {}).get("bin"),
        "card_last4": response_data.get("source", {}).get("last4"),
        "payment_scheme": get_payment_scheme(response_data.get("source", {})),
        "is_gcc_card": response_data.get("is_gcc_card"),
        "card_issuer_country": response_data.get("source", {}).get(
            "issuer_country")}
    logger.info(
        "structured dict for pre auth case {} ".format(structured_dict))
    return structured_dict


def get_payment_gateway_by_code(code):
    """get payment gateway object by code"""
    try:
        payment_gateway = PaymentGateway.objects.get(code=code)
    except PaymentGateway.DoesNotExist:
        payment_gateway = None
    return payment_gateway


def get_currency_by_iso_code(code):
    """get currency object by iso code"""
    try:
        currency = Currency.objects.get(iso_code=code)
    except Currency.DoesNotExist:
        currency = None
    return currency


def create_configuration_data(code, currency):
    """create configuration data"""
    from services.tasks import get_checkout_conf, get_b2c_conf
    config_data = None
    response = None
    if code == CHECKOUTPG_HUB_CODE:
        response = get_checkout_conf(currency)

    elif code == B2CPAYBACK_HUB_CODE:
        response = get_b2c_conf(currency)
    if response:
        payment_gateway = get_payment_gateway_by_code(code)
        currency_obj = get_currency_by_iso_code(currency)
        if payment_gateway and currency_obj:
            config_data = ConfigurationData(
                payment_gateway=payment_gateway,
                currency=currency_obj,
                response_data=response
            )
            config_data.save()
    return config_data


def get_configuration_data(code, currency):
    """get configuration data"""
    try:
        config_data = ConfigurationData.objects.get(
            payment_gateway__code=code, currency__iso_code=currency)
    except(ConfigurationData.DoesNotExist, Exception):
        logging.error(f'No configuration data instance found for code {code} '
                      f'and currency {currency}.')
        config_data = create_configuration_data(code, currency)
    return config_data


def encrypt_browser_value(string_value):
    key = BROWSER_VALUE_ENCRYPTION_KEY
    fer_instance = Fernet(key)
    encrypted_value = fer_instance.encrypt(string_value.encode())
    logger.info("encrypted browser value is {}".format(encrypted_value))
    return encrypted_value.decode("utf-8")


def decrypt_browser_value(encrypted_value):
    key = BROWSER_VALUE_ENCRYPTION_KEY
    fer_instance = Fernet(key)
    decrypted_value = fer_instance.decrypt(encrypted_value).decode()
    logger.info("decrypted cookie key is {}".format(decrypted_value))
    return decrypted_value


def get_display_platform(platform):
    """
    Converts platform to display it in required formats for clevertap.

    Args:
        platform (str): The platform stored ('Web', 'Mweb', 'Android', 'IOS').
    Returns:
        str: The display platform name ('WEB', 'MWEB', 'Android', 'iOS').
    """
    platform_map = {
        'Web': 'WEB',
        'Mweb': 'MWEB',
        'Android': 'Android',
        'IOS': 'iOS'
    }
    return platform_map.get(platform, platform)


def get_payment_scheme(response_data):
    """
    Determines the payment scheme based on the local scheme as
    PAYMENT_SCHEME_MADA is only available in local scheme.
    """
    if response_data.get("local_scheme") == PAYMENT_SCHEME_MADA:
        return PAYMENT_SCHEME_MADA
    else:
        response_data.get("payment_scheme")


def get_display_program(api_client):
    """
    Converts api_client name to display it in required formats for clevertap.
    Args:
        api_client (obj)
    Returns:
        str: The display api_client name if code present else client name
    """
    client_code = api_client.client_code

    api_client_map = {
        'ECOMORDS': 'Ecom',
        'EMAPIGRPGFT': 'Group Gift',
        'MYREWDB': 'Dukhan Bank',
        'MYREWPMI': 'PMI',
        'MYREWNBKM': '	NBK Miles',
        'MYREWVF': 'Vodafone',
        'MYREWNBUPP': 'NBK UEFA PWR PROGRAM',
        'MYREWSP': 'Spectrum',
        'MYREWNBK': 'NBK',
        'MYREWABKEM': 'ABK E-Mall',
    }
    program_name = api_client_map.get(client_code, None)

    if program_name:
        return program_name
    else:
        return api_client.name
