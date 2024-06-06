import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.constants import PAYMENT_STATUS_PAID, PAYMENT_STATUS_CANCELLED
from services.v1.views.common import YouPayTransactionCRUD
from .constant import (PAYMENT_STATUS_CHOICES, PAYMENT_STATUS_NONE,
                       PURCHASE_PLATFORM_CHOICES, TABBY_YOUPAY_STATUS_DICT,
                       PAYMENT_STATUS_CLOSED)

logger = logging.getLogger(__name__)

class TabbyPaymentData(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    order_reference = models.CharField(max_length=200, null=True,
                                       blank=True, )
    amount = models.DecimalField(decimal_places=4, max_digits=12, null=True,
                                 blank=True, )
    currency = models.CharField(max_length=3, null=True, blank=True, )
    customer_name = models.CharField(max_length=200, null=True, blank=True, )
    customer_email = models.CharField(max_length=500, null=True, blank=True, )
    customer_ip_address = models.CharField(max_length=50,
                                           null=True, blank=True)
    payment_id = models.CharField(
        max_length=200, blank=False, db_index=True,
        help_text='Payment id returns from Tabby')
    status = models.CharField(max_length=200, choices=PAYMENT_STATUS_CHOICES,
                              default=PAYMENT_STATUS_NONE, db_index=True,
                              help_text='Payment status')
    request_source = models.CharField(
        max_length=100, null=True, blank=True,
        help_text='Represent source from where this payment request '
                  'initiated')
    payment_reference = models.CharField(
        max_length=200, null=True, blank=True, db_index=True,
        help_text='Payment reference number')

    platform = models.CharField(max_length=50,
                                choices=PURCHASE_PLATFORM_CHOICES,
                                null=True, blank=True, db_index=True)
    is_paid = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is flagged or not.')
    invoice_id = models.CharField(max_length=200, blank=True, null=True,
                                  help_text="invoice id")

    def __str__(self):
        return self.payment_reference


@receiver(post_save, sender=TabbyPaymentData)
def update_youpaytransactiondata_on_webhook(sender, instance, created,
                                            **kwargs):
    payment_status = tabby_to_youpay_status(instance.status)
    if payment_status:
        try:
            youpay_crud = YouPayTransactionCRUD()
            transaction_obj = (
                youpay_crud.get_youpay_transaction_data_with_payment_reference(
                    instance.payment_reference))
            if transaction_obj:
                data_to_update = {
                    'transaction_id': transaction_obj.transaction_id,
                    "payment_status": payment_status
                }
                youpay_crud.update_youpay_transaction_data(
                            data_to_update)
                logger.info(
                    "Youpaytransactindata transaction {} updated with status"
                    " {}".format(
                        transaction_obj.transaction_id, payment_status))
            else:
                logger.info(
                    "Youpaytransaction object not found for payment reference "
                    "{} during update transaction from "
                    "TabbyPaymentData".format(instance.payment_reference))
        except Exception as e:
            logger.error(
                "Error while trying to update youpay transaction from "
                "TabbyPaymentData signal {}".format(e),exc_info=e)
    else:
        if instance.status == PAYMENT_STATUS_NONE:
            logger.info(
                "Skipped updating Youpaytransactiondata with tabbbypg status "
                "None for transaction {}".format(instance.payment_reference))
        else:
            logger.error(
                "Unable to update youpay transaction for reference {}, tabby"
                " payment status is {}".format(
                    instance.payment_reference, instance.status))


def tabby_to_youpay_status(tabbypg_data):
    tabbypg_status = tabbypg_data.get('status')
    is_paid = tabbypg_data.get('is_paid')

    payment_status = TABBY_YOUPAY_STATUS_DICT.get(tabbypg_status)
    if not payment_status:
        if tabbypg_status == PAYMENT_STATUS_NONE:
            payment_status = None
        logger.info(
            "Error status at tabbypgclient while trying to update "
            "youpaytransactiondata, status {}".format(tabbypg_status))

    if payment_status == PAYMENT_STATUS_CLOSED and is_paid:
        payment_status = PAYMENT_STATUS_PAID
    elif payment_status == PAYMENT_STATUS_CLOSED and not is_paid:
        payment_status = PAYMENT_STATUS_CANCELLED

    return payment_status
