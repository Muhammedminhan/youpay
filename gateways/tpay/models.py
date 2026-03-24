import logging
from decimal import Decimal

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import AbstractUserBase, AbstractDateTime, CustomerProfile
from payments.constants import PAYMENT_STATUS_PAID, PAYMENT_STATUS_DECLINED
from services.constants import TPAY_SUCCESS_CODES, PAYMENT_STATUS_INITIALIZED
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class TPayWebhookLog(AbstractDateTime):
    action = models.CharField(max_length=128, blank=True, null=True)
    payment_transaction_status_code = models.CharField(max_length=128)
    transaction_id = models.CharField(max_length=100, db_index=True)
    msisdn = models.CharField(max_length=20, blank=True, null=True)
    amount = models.CharField(max_length=32, null=True, blank=True)
    currency_code = models.CharField(max_length=15, null=True, blank=True)
    payment_date = models.CharField(max_length=128, null=True, blank=True)
    product_catalog_name = models.CharField(max_length=255, null=True,
                                            blank=True)
    product_id = models.CharField(max_length=128, null=True, blank=True)
    order_info = models.CharField(max_length=128, db_index=True)
    payment_provider_code = models.CharField(max_length=64, null=True,
                                             blank=True)

    digest = models.CharField(max_length=255, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"TPay Log {self.transaction_id} - {self.payment_transaction_status_code}"

@receiver(post_save, sender=TPayWebhookLog)
def update_tpay_transaction_from_log(sender, instance, created, **kwargs):
    """Webhook Log -> TPayTransaction"""
    try:
        tpay_tx = TPayTransaction.objects.filter(
            payment_reference=instance.order_info).first()
        if not tpay_tx:
            tpay_tx = TPayTransaction(payment_reference=instance.order_info)

        tpay_tx.tpay_transaction_id = instance.transaction_id
        tpay_tx.status = instance.payment_transaction_status_code
        tpay_tx.amount = Decimal(instance.amount) if instance.amount else 0
        tpay_tx.currency = instance.currency_code
        tpay_tx.msisdn = instance.msisdn
        tpay_tx.operator_code = instance.payment_provider_code
        tpay_tx.product_catalog = instance.product_catalog_name
        tpay_tx.raw_response = instance.payload
        tpay_tx.payment_date = instance.payment_date
        tpay_tx.save()
    except Exception as e:
        logger.error(f"Signal Error (Log to TPay): {e}")


class TPayTransaction(AbstractDateTime, AbstractUserBase, CustomerProfile):
    tpay_transaction_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text="Transaction ID returned by TPay system")
    payment_reference = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="OrderInfo sent to TPay (Merchant Order ID)")
    status = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Current status code/title")
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    currency = models.CharField(max_length=15, blank=True, null=True)
    msisdn = models.CharField(max_length=20, blank=True, null=True)
    operator_code = models.CharField(max_length=20, blank=True, null=True)
    product_catalog = models.CharField(max_length=255, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)
    payment_date = models.CharField(
        max_length=128, blank=True, null=True,
        help_text="Actual billing time sent by TPAY")
    youpay_transaction = models.ForeignKey(
        'payments.YouPayTransactionData', null=True, blank=True,
        on_delete=models.CASCADE)

    def __str__(self):
        return f"TPay {self.tpay_transaction_id} - {self.payment_reference}"


@receiver(post_save, sender=TPayTransaction)
def update_youpay_from_tpay(sender, instance, **kwargs):
    """TPayTransaction -> YouPayTransactionData"""
    try:
        crud = YouPayTransactionCRUD()
        transaction_obj = crud.get_youpay_transaction_data_with_payment_reference(
            instance.payment_reference)

        if (transaction_obj and not transaction_obj.is_payment_verified and
                instance.status != PAYMENT_STATUS_INITIALIZED):
            if instance.status in TPAY_SUCCESS_CODES:
                payment_status = PAYMENT_STATUS_PAID
                approved = True
            else:
                payment_status = PAYMENT_STATUS_DECLINED
                approved = False

            crud.update_youpay_transaction_data({
                'transaction_id': transaction_obj.transaction_id,
                'payment_status': payment_status,
                'approved': approved,
                'is_payment_verified': True,
                'response_summary': instance.status
            })
    except Exception as e:
        logger.error(f"Signal Error (TPay to YouPayTransactionData): {e}")
