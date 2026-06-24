import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CustomerProfile
from payments.models import YouPayTransactionData
from .choices import PaymentStatus


logger = logging.getLogger(__name__)


class NetworkTransaction(CustomerProfile):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    order_reference = models.CharField(max_length=200, db_index=True,
                                       help_text=_("Internal order reference"))
    payment_reference = models.CharField(max_length=200, unique=True,
                                         db_index=True, null=True,
                                         help_text=_("Unique reference for this payment attempt"))
    network_order_id = models.CharField(max_length=200, null=True, blank=True,
                                        db_index=True,
                                        help_text=_("Order ID from Network International"))
    network_order_reference = models.CharField(max_length=200, null=True,
                                               blank=True,
                                               help_text=_("Order reference from Network International"))

    amount = models.DecimalField(max_digits=12, decimal_places=4)
    currency = models.CharField(max_length=3, default='AED')
    youpay_transaction = models.ForeignKey(YouPayTransactionData,
                                           on_delete=models.CASCADE)
    status = models.CharField(
        max_length=50,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True
    )
    is_approved = models.BooleanField(default=False)
    youpay_transaction = models.ForeignKey(
        'payments.YouPayTransactionData', null=True,
        blank=True, on_delete=models.CASCADE,
        help_text='Related api Youpay transaction data')
    card_bin = models.CharField(max_length=10, null=True, blank=True)
    card_last4 = models.CharField(max_length=6, null=True, blank=True)
    card_scheme = models.CharField(max_length=50, null=True, blank=True)
    card_holder_name = models.CharField(max_length=200, null=True, blank=True)
    card_expiry_date = models.CharField(max_length=50, null=True, blank=True)
    card_issuer_country = models.CharField(max_length=50, null=True, blank=True)
    card_type = models.CharField(max_length=50, null=True, blank=True)
    is_gcc_card = models.BooleanField(default=False)
    auth_response_message = models.CharField(
        max_length=100, null=True, blank=True,
        help_text=_("Auth response message from Network International")
    )

    class Meta:
        verbose_name = _("Network Transaction")
        verbose_name_plural = _("Network Transactions")
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.payment_reference} - {self.status}"

    @property
    def redirect_url(self):
        if self.is_approved and self.status in [PaymentStatus.CAPTURED,
                                                PaymentStatus.AUTHORIZED]:
            return self.youpay_transaction.success_url
        else:
            return self.youpay_transaction.failure_url


class EventNotification(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    payment_reference = models.CharField(max_length=200, db_index=True, null=True, blank=True)
    event_type = models.CharField(max_length=100, null=True, blank=True)
    raw_data = models.JSONField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    event_id = models.CharField(max_length=100, null=True, blank=True)
    network_transaction = models.ForeignKey(NetworkTransaction,
                                            on_delete=models.CASCADE,
                                            null=True, blank=True)

    class Meta:
        verbose_name = _("Network Event Notification")
        verbose_name_plural = _("Network Event Notifications")

    def __str__(self):
        return f"{self.event_type} - {self.created_on}"
