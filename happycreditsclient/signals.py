import logging

from django.db.models import signals
from django.dispatch import receiver

from payments.constants import PAYMENT_STATUS_PAID
from payments.models import YouPayTransactionData
from .constants import HAPPY_CREDITS_STATUS_COMPLETED
from .models import HappyCreditsClientData

logger = logging.getLogger(__name__)


@receiver(signals.post_save, sender=HappyCreditsClientData)
def update_youpay_transaction_status(sender, instance, created, **kwargs):
    logger.info("Executing HappyCreditsClient signal")
    try:
        transaction_obj = YouPayTransactionData.objects.get(
            payment_reference=instance.payment_reference)
        check_status = (instance.status == HAPPY_CREDITS_STATUS_COMPLETED,
                        not
                        transaction_obj.payment_status == PAYMENT_STATUS_PAID)
        if all(check_status):
            transaction_obj.payment_status = PAYMENT_STATUS_PAID
            transaction_obj.save()
    except YouPayTransactionData.DoesNotExist:
        logger.error("Unable to find youpay transaction object for {}"
                     "".format(instance.payment_reference))
