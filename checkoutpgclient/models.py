
import logging
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext as _

from .constants import (PAYMENT_STATUS_CHOICES, PAYMENT_STATUS_NONE,
                        PAYMENT_STATUS_PAID, PAYMENT_METHOD_CHOICES,
                        PAYMENT_METHOD_CARD, PAYMENT_SCHEME_CHOICES,
                        PAYMENT_SCHEME_NONE)
logger = logging.getLogger(__name__)


class TransactionData(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    order_reference = models.CharField(max_length=200)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 db_index=True)
    currency = models.CharField(max_length=3, db_index=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.CharField(max_length=500, db_index=True)
    idempotency_key = models.CharField(
        max_length=200, blank=False, default=None,
        help_text=_('Unique key to avoid duplicate payment happening due to '
                    'network error or timeout. Recommend to use V4 UUIDs.'))
    payment_reference = models.CharField(
        max_length=200, blank=False, db_index=True,
        help_text=_('Payment reference number'))
    request_source = models.CharField(
        max_length=100, null=True, blank=True,
        help_text=_('Represent source from where this payment request '
                    'initiated'))
    api_request_data = models.TextField(
        null=True, blank=True, help_text=_('Payment API request data'))
    api_response_data = models.TextField(
        null=True, blank=True, help_text=_('Payment API response data'))
    is_notification = models.BooleanField(default=False)
    approved = models.BooleanField(
        default=False,
        help_text=_('Denotes whether the payment is approved or not'))
    status = models.CharField(max_length=200, choices=PAYMENT_STATUS_CHOICES,
                              default=PAYMENT_STATUS_NONE, db_index=True,
                              help_text=_('Payment status'))
    auth_code = models.CharField(
        max_length=50, null=True, blank=True,
        help_text=_('The acquirer authorization code, if the payment '
                    'was authorized.'))
    response_summary = models.CharField(
        max_length=500, null=True, blank=True,
        help_text=_('Checkout response summary text'))
    invoice_id = models.CharField(
        max_length=50, null=True, blank=True, db_index=True,
        help_text=_('invoice pk that response associated with'))
    is_fraud = models.BooleanField(
        default=False, db_index=True,
        help_text=_('Denotes whether the payment is fraud or not.'))
    is_flagged = models.BooleanField(
        default=False, db_index=True,
        help_text=_('Denotes whether the payment is marked as flagged '
                    'or not.'))
    is_flagged_email_sent = models.BooleanField(
        default=False, db_index=True,
        help_text=_('Denotes whether the flagged payment email sent or not'))
    card_bin = models.CharField(
        max_length=6, null=True, blank=True,
        db_index=True, help_text=_(
            'Denotes the bin number of the card used for the payment'))
    card_last4 = models.CharField(max_length=4, null=True, blank=True,
                                  db_index=True,
                                  help_text=_(
                                      'Denotes the last 4 digits of the card'
                                      ' used for the payment'))
    payment_method = models.CharField(max_length=200,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      default=PAYMENT_METHOD_CARD,
                                      db_index=True,
                                      help_text=_('Payment Method'))
    payment_scheme = models.CharField(
        max_length=200,
        choices=PAYMENT_SCHEME_CHOICES,
        default=PAYMENT_SCHEME_NONE,
        db_index=True,
        help_text=_('Denotes the payment scheme used for the payment'))

