import uuid
import logging

from django.db.models import signals
from django.dispatch import receiver
from django.db import models

from core.models import AbstractDateTime
from core.validators import DecimalValidator
from payments.models import YouPayTransactionData
from payments.constants import PAYMENT_STATUS_CAPTURED, PAYMENT_STATUS_PAID

logger = logging.getLogger(__name__)


class HappyCreditsClientData(AbstractDateTime):
    request_data = models.JSONField(
        null=True, blank=True, help_text="used to store webhook request data")
    payment_reference = models.CharField(
        max_length=120, blank=False, db_index=True,
        help_text='Payment reference number')
    # status = models.CharField(max_length=200, choices=PAYMENT_STATUS_CHOICES,
    #                           default=PAYMENT_STATUS_NONE, db_index=True,
    #                           help_text='Payment status')

    def __str__(self):
        return self.payment_reference


# @receiver(signals.post_save, sender=AmazonPGTransactionData)
# def update_youpay_status(sender, instance, created, **kwargs):
#
#     logger.info("Executing AmazonPGTransactionData signal")
#     try:
#         transaction_obj = YouPayTransactionData.objects.get(
#             payment_reference=instance.payment_reference)
#         if instance.payment_status == PAYMENT_STATUS_CAPTURED:
#             transaction_obj.payment_status = PAYMENT_STATUS_PAID
#         else:
#             transaction_obj.payment_status = instance.payment_status
#         if not transaction_obj.card_bin:
#             transaction_obj.card_bin = instance.card_bin
#             transaction_obj.card_last4 = instance.card_last4
#         transaction_obj.save()
#     except YouPayTransactionData.DoesNotExist:
#         logger.error("Unable to find youpay transaction object for {}"
#                      "".format(instance.payment_reference))
