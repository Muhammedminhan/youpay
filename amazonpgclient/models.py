import logging
import uuid

from django.db import models
from django.db.models import signals
from django.dispatch import receiver

from core.models import AbstractDateTime, CustomerProfile
from .constants import (TRANSACTION_PAYMENT_STATUS_CHOICES,
                        APG_PAYMENT_TRANSACTION_STATUS_CHOICES)
from payments.models import YouPayTransactionData
from payments.constants import (PAYMENT_STATUS_CAPTURED, PAYMENT_STATUS_PAID,
                                PAYMENT_STATUS_FAILED,
                                PAYMENT_STATUS_CANCELLED)

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
def youpay_transaction_data_post_save_on_webhook(sender, instance, created,
                                                 **kwargs):
    payment_reference = None

    logger.info("Executing AmazonPGTransactionData signal")
    try:
        logger.info(
            "AmazonPGTransactionData post_save Triggering for "
            "reference {}, status {}".format(
                instance.payment_reference, instance.payment_status))

        from services.v1.views.common import YouPayTransactionCRUD

        payment_reference = instance.payment_reference
        youpay_obj = YouPayTransactionCRUD()
        data_to_update = prepare_youpay_transaction_update_data(
            instance, payment_reference, youpay_obj)
        if data_to_update:
            transaction_id = data_to_update.get('transaction_id')
            is_youpay_updated = youpay_obj.update_youpay_transaction_data(
                data_to_update)
            if is_youpay_updated:
                logger.info(
                    "AmazonPGTransactionData post_save success for "
                    "reference {}, status {}".format(
                        instance.payment_reference, instance.payment_status))
    except Exception as e:
        logger.error(
            "Exception : AmazonPGTransactionData post_save for "
            "payment reference {}, error :{}".format(
                payment_reference, str(e)), exc_info=True)


def prepare_youpay_transaction_update_data(instance, payment_reference,
                                           youpay_obj):
    try:
        transaction_obj = (
            youpay_obj.get_youpay_transaction_data_with_payment_reference(
                payment_reference))
        if instance.payment_status == PAYMENT_STATUS_CAPTURED:
            payment_status = PAYMENT_STATUS_PAID
        elif instance.payment_status == PAYMENT_STATUS_CANCELLED:
            payment_status = PAYMENT_STATUS_FAILED
        else:
            payment_status = instance.payment_status

        if transaction_obj:
            data_to_update = {
                'transaction_id': transaction_obj.transaction_id,
                "payment_status": payment_status,
                "payment_reference": instance.payment_reference,
                "response_summary": instance.response_message,
                "card_last4": instance.card_last4,
                "card_bin": instance.card_bin,
            }
            return data_to_update
        else:
            logger.info(
                "Transaction object not found for payment reference "
                "{}".format(payment_reference))
            return None
    except Exception as e:
        logger.error("Error while preparing data for youpay transaction "
                     "update {}".format(e), exc_info=True)
