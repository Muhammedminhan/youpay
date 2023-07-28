import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.constants import MODEL_NAME_ADCBTRANSACTIONDATA
from payments.models import YouPayTransactionData
from .constants import (PURCHASE_PLATFORM_CHOICES, REDEMPTION_METHOD_CHOICES,
                        REDEMPTION_METHOD_NONE)

logger = logging.getLogger(__name__)

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
        default=False, null=True, blank=True,
        help_text='Denotes the redemption is completed')
    payment_status = models.BooleanField(
        default=False, null=True, blank=True,
        help_text='Denotes the payment is completed')
    redemption_method = models.CharField(
        max_length=50, default=REDEMPTION_METHOD_NONE,
        choices=REDEMPTION_METHOD_CHOICES)
    customer_email = models.CharField(
        max_length=500, null=True, blank=True)
    auth_code = models.CharField(
        max_length=50, null=True, blank=True,
        help_text='The acquirer authorization code, if the payment '
                  'was authorized.')
    is_fraud = models.BooleanField(
        default=False, db_index=True, null=True, blank=True,
        help_text='Denotes whether the payment is fraud or not.')
    is_flagged = models.BooleanField(
        default=False, db_index=True, null=True, blank=True,
        help_text='Denotes whether the payment is marked as flagged '
                  'or not.')
    card_issuer_country = models.CharField(
        max_length=4, null=True, blank=True, db_index=True,
        help_text=' Denotes two letter code card issued country.')
    payment_id = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='for checkoutpg transactions, payment id received from '
                  'checkout.com')
    financial_action_response_data = models.JSONField(
        null=True, blank=True,
        help_text='for checkoutpg transactions, response data received after '
                  'calling financial-actions api.')
    gateway_fee_authorization = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway authorization fee from financial "
                  "action data")
    gateway_fee_void = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway void fee from financial "
                  "action data")
    gateway_fee_refund = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway refund fee from financial "
                  "action data")
    blended_variable_fee = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store blended variable fee from financial "
                  "action data")
    gateway_fee_authorization_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway authorization fee vat from financial"
                  " action data")
    gateway_fee_void_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway void fee vat from financial "
                  "action data")
    gateway_fee_refund_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store gateway refund fee vat from financial "
                  "action data")
    blended_variable_fee_vat = models.DecimalField(
        decimal_places=8, max_digits=12, null=True, blank=True,
        help_text="Used to store blended variable fee vat from financial "
                  "action data")
    card_category = models.CharField(
        max_length=20, null=True, blank=True,
        help_text='Denotes the card category i.e. consumer/commercial')
    entity_id = models.CharField(
        max_length=40, null=True, blank=True,
        help_text='The unique id related to the merchant account')
    issuer_bank = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='Denotes the card issued bank.'
    )
    cvv_check = models.CharField(
        max_length=10, null=True, blank=True,
        help_text='cvv check info.'
    )
    three_ds_check = models.BooleanField(default=False, null=True, blank=True)


@receiver(post_save, sender=ADCBTransactionData)
def calculate_adcb_card_charges(sender, instance, created, **kwargs):
    if instance.financial_action_response_data:
        from payments.tasks import common_update_financial_action_charges
        try:
            logger.info("adcbpgclient updated with financial action data")
            from payments.tasks import update_calculated_gateway_charges
            transaction_obj = YouPayTransactionData.objects.get(
                payment_reference=instance.reference_id)
            update_calculated_gateway_charges(transaction_obj.transaction_id)
            fin_args = {
                "pk": instance.id,
                "financial_action_data": (
                    instance.financial_action_response_data),
                "model_name": MODEL_NAME_ADCBTRANSACTIONDATA
            }
            common_update_financial_action_charges.delay(**fin_args)
        except Exception as e:
            logger.error("Error calling gateway charge calculation for "
                         "adcb transaction {}".format(instance.reference_id),
                         exc_info=e)
