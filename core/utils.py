import json
import logging

import redis

from contextlib import contextmanager
from time import sleep
from base64 import b64decode, b64encode
from functools import wraps
from os import urandom

from Crypto.Cipher import AES
from cryptography.fernet import Fernet
from django.core.cache import cache
from django.conf import settings

from core.constants import COMMON_ENCRYPTION_KEY, FERNET_KEY
from core.models import AppConfig
from integrations.constants import CHECKOUTPG_HUB_CODE, TABBYPG_HUB_CODE
from integrations.models import PaymentGateway, AdditionalFee

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


def get_gateway_additional_fee(payment_option):
    """
    :param payment option
    :return:
    """
    additional_fee = None
    if payment_option:
        try:
            additional_fee = AdditionalFee.objects.get(
                payment_option__name=payment_option)
        except(AdditionalFee.DoesNotExist, Exception):
            logging.error('No additional fee instance found.')
            return None
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
        logger.error("string decryption failed. {}".format(e))
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
    return url +'?transaction_id=' + transaction_id
