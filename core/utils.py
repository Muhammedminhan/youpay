import json
import logging
from base64 import b64decode, b64encode
from functools import wraps
from os import urandom

logger = logging.getLogger(__name__)
from Crypto.Cipher import AES

from core.constants import COMMON_ENCRYPTION_KEY


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
    input : encrypted data : json
    output : decrypted data

    After Modification:
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
    Parameters:
        raw : the payment request json data
    Returns:
        json with the encrypted data, nonce and tag

    After Modification:
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


a = """{
  "payment": {
    "product_code": "",
    "payment_platform": "IOS",
    "ip": "192.168.1.1",
    "language": "en",
    "invoice_id": "1234",
    "order_reference": "Gift-1234-ecom"
  },
  "order": {
    "amount": 123,
    "currency": "AED",
    "service_fee": 123,
    "base_amount": 2344,
    "VAT": 2343
  },
  "customer": {
    "email": "jomon@yougotagift.com",
    "phone": 12324234,
    "name": "jomon",
    "registered_since": "26-03-1994"
  },
  "order_history": {
    "total_items": 2,
    "items": [
      {
        "tittle": "item 1",
        "category": "electronic-gift",
        "ref_id": "item-123"
      },
      {
        "tittle": "item 2",
        "category": "electronic-gift",
        "ref_id": "item-124"
      },
      {
        "tittle": "item 3",
        "category": "electronic-gift",
        "ref_id": "item-125"
      }
    ]
  },
  "order_items": {
    "items": [
      {
        "tittle": "item 1",
        "category": "electronic-gift",
        "ref_id": "item-123"
      },
      {
        "tittle": "item 2",
        "category": "electronic-gift",
        "ref_id": "item-124"
      },
      {
        "tittle": "item 3",
        "category": "electronic-gift",
        "ref_id": "item-125"
      }
    ]
  },
  "api_client": 37,
  "amount":110.00,
  "invoice_id":12345,
  "currency":"AED",
  "order_reference":"Gift-1234-ecom",
  "customer_email":"",
  "customer_phone":"",
  "language":"en",
  "platform":"IOS",
  "payment_gateway":"tabbypg",
  "session_id":"sessionid"
}"""
