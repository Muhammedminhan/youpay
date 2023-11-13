from django.db import models

from adcbpgclient.constants import (
    PURCHASE_PLATFORM_CHOICES, REDEMPTION_METHOD_NONE,
    REDEMPTION_METHOD_CHOICES)
from adcbpgclient.models import (DECIMAL_MAX_DIGITS, DECIMAL_PLACES,
                                 ADCBAbstractDateTime)


class PaybackRedemptionData(ADCBAbstractDateTime):
    request_id = models.CharField(max_length=50, db_index=True, unique=True)
    invoice = models.CharField(max_length=50)
    reference_id = models.CharField(max_length=50, db_index=True)
    platform = models.CharField(max_length=50,
                                choices=PURCHASE_PLATFORM_CHOICES)
    customer_name = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Denotes the actual amount to pay')
    currency = models.CharField(null=True, blank=True, max_length=10,
                                help_text='Denotes the actual currency to pay')
    amount_in_aed = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Denotes converted amount to AED')
    redemption_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='amount to redeem from b2c payback')
    redeemed_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='amount which is redeemed on '
                                         'b2c payback')
    redeemed_points = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='points which is redeemed by '
                                         'b2c payback')
    redemption_method = models.CharField(max_length=50,
                                         default=REDEMPTION_METHOD_NONE,
                                         choices=REDEMPTION_METHOD_CHOICES)
    customer_email = models.CharField(max_length=500, null=True, blank=True)
    available_points = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Available points for the card')
    available_amount = models.DecimalField(
        max_digits=DECIMAL_MAX_DIGITS, decimal_places=DECIMAL_PLACES,
        null=True, blank=True, help_text='Available amounts for the card')
    is_full_redemption = models.BooleanField(
        db_index=True, null=True, blank=True,
        help_text='Denotes whether the redemption is full or not.')
    redemption_status = models.BooleanField(
        default=False,
        help_text='Denotes the redemption is completed')

    class Meta:
        abstract = True


class CitiRedemptionData(PaybackRedemptionData):
    customer_phone = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Store customer mobile number used to send the otp for MFA")
    card_last4 = models.CharField(max_length=6, null=True, blank=True)
    control_flow_id = models.CharField(
        max_length=300, null=True, blank=True,
        help_text=('Store citi rewards control flow id received '
                   'from otp generation api.'))
    maximum_redeemable_points = models.DecimalField(
        null=True, blank=True, decimal_places=4, max_digits=15,
        help_text='Maximum points used for citi rewards point redemption')
    minimum_redeemable_points = models.DecimalField(
        null=True, blank=True, decimal_places=4, max_digits=15,
        help_text='Minimum points used for citi rewards point redemption')
    amount_conversion_rate = models.FloatField(
        null=True, blank=True, help_text=('Conversion rate received from '
                                          'citi rewards point balance api'))
    card_id = models.CharField(
        max_length=1000, null=True, blank=True,
        help_text=('Store citi rewards card id received from '
                   'point balance api.'))
    point_transfer_enabled = models.BooleanField(
        default=False,
        help_text='stores citi rewards point transfer eligible flag')
    pay_with_points_enabled = models.BooleanField(
        default=False,
        help_text='stores citi rewards pay with points eligible flag')
    convert_cash_enabled = models.BooleanField(
        default=False,
        help_text='stores citi rewards convert to cash eligible flag')
    citi_access_token = models.CharField(
        max_length=1000, null=True, blank=True,
        help_text='stores citi rewards access token')
    citi_token_type = models.CharField(
        max_length=10, null=True, blank=True,
        help_text='Denotes citi rewards token type')
    citi_order_id = models.CharField(
        max_length=300, null=True, blank=True,
        help_text='Order id received from citi rewards redemption api')
