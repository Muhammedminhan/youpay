import uuid
import logging

from django.db.models import signals
from django.dispatch import receiver
from django.db import models

from core.models import AbstractDateTime
from payments.constants import PAYMENT_STATUS_PAID
from payments.models import YouPayTransactionData
from .constants import (HAPPY_CREDITS_STATUS_CHOICE,
                        HAPPY_CREDITS_STATUS_PENDING,
                        HAPPY_CREDITS_STATUS_COMPLETED)

logger = logging.getLogger(__name__)


class HappyCreditsClientData(AbstractDateTime):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False,
                                      unique=True)
    customer_email = models.CharField(max_length=500, db_index=True)
    request_data = models.JSONField(
        null=True, blank=True, help_text="used to store webhook request data")
    payment_reference = models.CharField(
        max_length=120, blank=False, db_index=True,
        help_text='Payment reference number')
    status = models.CharField(max_length=200, db_index=True,
                              choices=HAPPY_CREDITS_STATUS_CHOICE,
                              default=HAPPY_CREDITS_STATUS_PENDING,
                              help_text='Payment status')

    def __str__(self):
        return self.payment_reference


@receiver(signals.post_save, sender=HappyCreditsClientData)
def update_youpay_status(sender, instance, created, **kwargs):

    logger.info("Executing HappyCreditsClient signal")
    try:
        transaction_obj = YouPayTransactionData.objects.get(
            payment_reference=instance.payment_reference)
        if instance.status == HAPPY_CREDITS_STATUS_COMPLETED:
            transaction_obj.payment_status = PAYMENT_STATUS_PAID
        else:
            transaction_obj.payment_status = instance.status
        transaction_obj.save()
    except YouPayTransactionData.DoesNotExist:
        logger.error("Unable to find youpay transaction object for {}"
                     "".format(instance.payment_reference))
