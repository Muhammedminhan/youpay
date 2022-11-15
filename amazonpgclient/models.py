import uuid
import logging

from django.db.models import signals
from django.dispatch import receiver
from django.db import models

from core.models import AbstractDateTime, CustomerProfile
from .constants import (TRANSACTION_PAYMENT_STATUS_CHOICES,
                        APG_PAYMENT_TRANSACTION_STATUS_CHOICES)
from payments.models import YouPayTransactionData

logger = logging.getLogger(__name__)


class AmazonPGTransactionData(AbstractDateTime, CustomerProfile):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False,
                                      unique=True)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 help_text="used to store total order amount")
    currency = models.CharField(null=False, blank=False, max_length=15,
                                help_text="used to store currency details")
    invoice_id = models.CharField(max_length=120, null=True, blank=True)
    order_reference = models.CharField(max_length=120, null=True, blank=True,
                                       db_index=True)
    payment_reference = models.CharField(max_length=120, null=True,
                                         blank=True, db_index=True)
    fort_id = models.CharField(max_length=20, blank=False, null=True,
                               help_text='The order’s unique reference '
                                         'returned by amazon payment '
                                         'gateway.', db_index=True)
    payment_status = models.CharField(
        max_length=20, null=True, blank=True,
        choices=TRANSACTION_PAYMENT_STATUS_CHOICES)
    apg_payment_status = models.CharField(
                            max_length=20, null=True, blank=True,
                            choices=APG_PAYMENT_TRANSACTION_STATUS_CHOICES)
    card_bin = models.CharField(max_length=6, null=True, blank=True,
                                help_text='Denotes the bin number of the '
                                          'card used for the payment')
    card_last4 = models.CharField(max_length=4, null=True, blank=True,
                                  help_text='Denotes the last 4 digits of the'
                                            ' card used for the payment')
    authorization_code = models.CharField(
        max_length=100, null=True, blank=True,
        help_text='The authorization code returned from the 3rd party.')
    response_code = models.CharField(
        max_length=5, null=True, blank=True,
        help_text='Denotes the response code received from APG')
    response_message = models.CharField(
        max_length=150, null=True, blank=True,
        help_text='Denotes the response message received from APG')
    acquirer_response_code = models.CharField(
        max_length=10, null=True, blank=True,
        help_text='Denotes the response received from APG')

    def __str__(self):
        return self.payment_reference


@receiver(signals.post_save, sender=AmazonPGTransactionData)
def update_youpay_status(sender, instance, created, **kwargs):

    logger.info("Executiong AmazonPGTransactionData signal")
    try:
        transaction_obj = YouPayTransactionData.objects.get(
            payment_reference=instance.payment_reference)
        transaction_obj.payment_status = instance.payment_status
        transaction_obj.save()
    except YouPayTransactionData.DoesNotExist:
        logger.error("Unable to find youpay transaction object for {}"
                     "".format(instance.payment_reference))
