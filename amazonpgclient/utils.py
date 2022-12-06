import logging
from contextlib import contextmanager
from time import sleep

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


@contextmanager
def wait_lock(
        lock_name, lock_timeout=settings.WAIT_LOCK_DEFAULT_TIMEOUT,
        wait_duration=settings.WAIT_LOCK_DEFAULT_WAIT_DURATION,
        max_retries=settings.WAIT_LOCK_DEFAULT_MAX_RETRIES):
    """
    Executes code if lock `lock_name` isn't set, else it retries after
    `wait_duration` seconds.
    Context manager for making sure only one single process/thread
    executes a piece of code with a given `lock_name`.  If the lock for
    the process is already set then it waits for `wait_duration` seconds
    up to `max_retries` times.  To prevent the lock from being set for a
    long time, in case of errors, it will expire after `lock_timeout`
    seconds.
    """
    redis_conn = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT,
        db=settings.REDIS_LOCKS_DB
    )

    retries = 0
    while redis_conn.get(lock_name):
        if retries < max_retries:
            logger.debug("Lock exists...sleeping.")
            sleep(wait_duration)
            retries += 1
        else:
            raise WaitLockException('Unable to acquire lock.')

    redis_conn.setex(lock_name, lock_timeout, '1')
    try:
        yield
    finally:
        redis_conn.delete(lock_name)


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
