import logging

from datetime import timedelta
from celery import shared_task
from payments.models import YouPayTransactionData
from payments.constants import (PAYMENT_STATUS_INITIATED,
                                PAYMENT_STATUS_EXPIRED)
from django.db.models.functions import Now

logger = logging.getLogger(__name__)


@shared_task(name='set_transaction_expired')
def set_transaction_expired():
    """
        Method to set payment_status of all YouPayTransactionData objects
        older than 20 minutes to expired status.
    """
    YouPayTransactionData.objects.filter(
        payment_status=PAYMENT_STATUS_INITIATED,
        created_at__lt=Now()-timedelta(minutes=2)).update(
        payment_status=PAYMENT_STATUS_EXPIRED)
    logger.info("youpay transactions older than 20 minutes set to "
                "expired status")
    return True
