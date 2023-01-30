from django.db import models
from .constants import (PURCHASE_PLATFORM_CHOICES, REDEMPTION_METHOD_CHOICES,
                        REDEMPTION_METHOD_NONE)

DECIMAL_MAX_DIGITS = 15
DECIMAL_PLACES = 2


class ADCBAbstractDateTime(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ADCBTransactionData(ADCBAbstractDateTime):
    request_id = models.CharField(
        max_length=50, db_index=True, null=True, blank=True)
    invoice = models.CharField(
        max_length=50, null=True, blank=True)
    reference_id = models.CharField(
        max_length=50, db_index=True, null=True, blank=True)
    card_number = models.CharField(
        max_length=20, null=True, blank=True)
    card_expiry = models.CharField(
        max_length=20, null=True, blank=True)
    encrypted_card_number = models.CharField(
        max_length=70, null=True, blank=True)
    encrypted_card_expiry = models.CharField(
        max_length=70, null=True, blank=True)
    platform = models.CharField(
        max_length=50, null=True, blank=True,
        choices=PURCHASE_PLATFORM_CHOICES)
    customer_name = models.CharField(
        max_length=100, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Denotes the actual amount to pay')
    currency = models.CharField(
        null=True, blank=True, max_length=10,
        help_text='Denotes the actual currency to pay')
    amount_in_aed = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Denotes converted amount to AED')
    redemption_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='amount to be redeemed from ADCB')
    redeemed_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='amount redeemed on ADCB')
    redeemed_points = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='points redeemed on ADCB')
    payable_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True,
        help_text='amount which is paid using credit/debit card by '
                  'the customer')
    available_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Available amounts for the card')
    available_points = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Available points for the card')
    is_full_redemption = models.BooleanField(
        db_index=True, null=True, blank=True,
        help_text='Denotes whether the redemption is full or not.')
    redemption_status = models.BooleanField(
        default=False,
        help_text='Denotes the redemption is completed')
    payment_status = models.BooleanField(
        default=False,
        help_text='Denotes the payment is completed')
    redemption_method = models.CharField(
        max_length=50, default=REDEMPTION_METHOD_NONE,
        choices=REDEMPTION_METHOD_CHOICES)
    customer_email = models.CharField(
        max_length=500, null=True, blank=True)
