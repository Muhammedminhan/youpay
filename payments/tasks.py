import logging

from datetime import timedelta
from celery import shared_task
from payments.models import YouPayTransactionData
from payments.constants import (PAYMENT_STATUS_INITIATED,
                                PAYMENT_STATUS_PENDING,
                                PAYMENT_STATUS_EXPIRED,
                                TRANSACTION_EXPIRE_TIME)
from django.db.models.functions import Now
from core.utils import wait_redis_lock

logger = logging.getLogger(__name__)


@shared_task(name='set_transaction_expired')
def set_transaction_expired():
    """
        Method to set payment_status of all YouPayTransactionData objects
        older than 20 minutes to expired status.
    """
    logger.info("cronjob for setting youpay transactions older than 20 "
                "minutes to expired status started")
    lock_name = 'lock:expire_payment_cronjob:id %s' % (
        set_transaction_expired.request.id)
    try:
        with wait_redis_lock(lock_name=lock_name):
            payment_statuses = [PAYMENT_STATUS_INITIATED,
                                PAYMENT_STATUS_PENDING ]
            transaction_objs = YouPayTransactionData.objects.filter(
                payment_status__in=payment_statuses,
                updated_at__lt=Now()-timedelta(minutes=TRANSACTION_EXPIRE_TIME))
            if transaction_objs:
                transaction_ids = []
                for obj in transaction_objs:
                    transaction_ids.append(str(obj.transaction_id))
                    obj.payment_status = PAYMENT_STATUS_EXPIRED
                    obj.save()
                logger.info("cronjob has set transactions {} to expired "
                            "status".format(transaction_ids))
            return True
    except Exception as e:
        logger.error("Error occurred during expire payment cronjob",
                     exc_info=e)
