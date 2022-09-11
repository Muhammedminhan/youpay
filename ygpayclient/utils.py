import json
import logging
import redis

from django.conf import settings
from contextlib import contextmanager
from time import sleep
from Crypto.Cipher import AES
from base64 import b64encode, b64decode
from os import urandom
from .constants import COMMON_ENCRYPTION_KEY

logger = logging.getLogger(__name__)


class ProcessPaymentData(object):
    """
    this class  is for process payment request data
    """

    def __init__(self):
        self.key = COMMON_ENCRYPTION_KEY

    def encrypt_payment_data(self, raw):
        """
        This method is to encrypt the request data.

        Parameters:
            raw : the payment request dictionary data
        Returns:
            encrypted data, nonce and tag - str
        """
        raw_text = json.dumps(raw)  # convert input dict to string
        iv = urandom(12)
        cipher = AES.new(self.key.encode("utf8"), AES.MODE_GCM, iv)
        ciphertext, tag = cipher.encrypt_and_digest(raw_text.encode("utf8"))
        json_k = ['nonce', 'ciphertext', 'tag']
        json_v = [b64encode(x).decode('utf-8') for x in
                  [cipher.nonce, ciphertext, tag]]
        encrypted_data = json.dumps(dict(zip(json_k, json_v)))
        return encrypted_data

    def decrypt_payment_data(self, encrypted_data):
        """
        This method is to decrypt the request data.

        Parameters:
            encrypted_data : the encrypted json data with nonce and tag
        Returns:
            Decrypted data
        """
        try:
            b64 = json.loads(encrypted_data)
            json_k = ['nonce', 'ciphertext', 'tag']
            jv = {k: b64decode(b64[k]) for k in json_k}
            cipher = AES.new(self.key.encode("utf8"), AES.MODE_GCM,
                             nonce=jv['nonce'])
            plaintext = cipher.decrypt_and_verify(jv['ciphertext'], jv['tag'])
            decrypted_data = json.loads(plaintext.decode("utf8"))
            return decrypted_data
        except (ValueError, KeyError):
            logger.error("request data decryption failed.")
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
            raise Exception('Unable to acquire lock.')
    try:
        yield
    finally:
        redis_conn.delete(lock_name)
