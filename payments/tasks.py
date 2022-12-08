import logging

from datetime import timedelta
from celery import shared_task
from payments.models import YouPayTransactionData
from payments.constants import (PAYMENT_STATUS_INITIATED,
                                PAYMENT_STATUS_EXPIRED,
                                TRANSACTION_EXPIRE_TIME)
from django.db.models.functions import Now

logger = logging.getLogger(__name__)


@shared_task(name='set_transaction_expired')
def set_transaction_expired():
    """
        Method to set payment_status of all YouPayTransactionData objects
        older than 20 minutes to expired status.
    """
    logger.info("cronjob for setting youpay transactions older than 20 "
                "minutes to expired status started")
    transaction_objs = YouPayTransactionData.objects.filter(
        payment_status=PAYMENT_STATUS_INITIATED,
        created_at__lt=Now()-timedelta(minutes=TRANSACTION_EXPIRE_TIME))
    if transaction_objs:
        transaction_ids = [str(obj.transaction_id) for obj in
                           transaction_objs]
        transaction_objs.update(payment_status=PAYMENT_STATUS_EXPIRED)
        logger.info("cronjob has set transactions {} to expired "
                    "status".format(transaction_ids))
    else:
        logger.info("No transactions were set to expired status by cronjob")
    return True
