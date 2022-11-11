from django.db import models
from .constant import (PAYMENT_STATUS_CHOICES,
                       PAYMENT_STATUS_NONE,
                       PURCHASE_PLATFORM_CHOICES)


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
