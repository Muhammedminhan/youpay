from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractDateTime(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class YGPayClientTransactionData(AbstractDateTime):
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment_reference = models.CharField(
        max_length=200, null=True, blank=True)
    order_reference = models.CharField(
        max_length=200, null=True, blank=True)
    invoice_id = models.CharField(
        max_length=100, null=True, blank=True)
    api_client = models.CharField(max_length=100, null=True, blank=True)

    amount = models.DecimalField(decimal_places=4, max_digits=12)
    currency = models.CharField(max_length=5, null=True, blank=True)
    service_fee = models.DecimalField(decimal_places=4, max_digits=12)
    base_amount = models.DecimalField(decimal_places=4, max_digits=12)
    vat_amount = models.DecimalField(decimal_places=4, max_digits=12)

    customer_ip_address = models.CharField(
        max_length=100, null=True, blank=True)
    customer_email = models.CharField(max_length=200, null=True, blank=True)
    order_history = models.JSONField(
        null=True, blank=True, help_text=_('Order history items'))

    payment_gateway = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.transaction_id)
