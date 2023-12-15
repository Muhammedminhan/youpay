import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from adcbpgclient.constants import (
    PURCHASE_PLATFORM_CHOICES, REDEMPTION_METHOD_NONE,
    REDEMPTION_METHOD_CHOICES)
from adcbpgclient.models import (DECIMAL_MAX_DIGITS, DECIMAL_PLACES,
                                 ADCBAbstractDateTime)
from citirewardsclient.constants import (
    CITI_TRANSACTION_PAYMENT_STATUS_CHOICES)
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


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
    payment_status = models.CharField(
        max_length=20, null=True, blank=True,
        choices=CITI_TRANSACTION_PAYMENT_STATUS_CHOICES)
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


@receiver(post_save, sender=CitiRedemptionData)
def youpay_transaction_data_post_save_on_webhook(sender, instance, created,
                                                 **kwargs):
    payment_reference = None
    transaction_id = None
    is_success, is_youpay_updated = False, False

    try:
        logger.info(
            "Citi Redemption Data post_save Triggering for "
            "reference {}, status {}".format(
                instance.reference_id, instance.payment_status))

        payment_reference = instance.reference_id

        youpay_obj = YouPayTransactionCRUD()

        data_to_update = prepare_youpay_transaction_update_data(
            instance, payment_reference, youpay_obj)

        if data_to_update:
            transaction_id = data_to_update.get('transaction_id')
            is_youpay_updated = youpay_obj.update_youpay_transaction_data(
                data_to_update)
            is_success = True
    except Exception as e:
        logger.error(
            "Exception : Citi Redemption Data post_save for "
            "payment reference {}, error :{}".format(
                payment_reference, str(e)), exc_info=True)
        is_success = False
    finally:
        logger.info(
            "Citi Redemption Data post_save Triggered for tid {}, "
            "reference {}, is_completed {}, youpay updated {}".format(
                transaction_id, payment_reference, is_success,
                is_youpay_updated))


def prepare_youpay_transaction_update_data(instance, payment_reference,
                                           youpay_obj):
    try:
        transaction_obj = (
            youpay_obj.get_youpay_transaction_data_with_payment_reference(
                payment_reference))
        if transaction_obj:
            data_to_update = {
                'transaction_id': transaction_obj.transaction_id,
                "payment_status": instance.payment_status,
                "reference_id": instance.reference_id,
                "customer_phone": instance.customer_phone,
                "maximum_redeemable_points": instance.maximum_redeemable_points,
                "minimum_redeemable_points": instance.minimum_redeemable_points,
                "amount_conversion_rate": instance.amount_conversion_rate,
                "point_transfer_enabled": instance.point_transfer_enabled,
                "pay_with_points_enabled": instance.pay_with_points_enabled,
                "convert_cash_enabled": instance.convert_cash_enabled,
                "card_last4": instance.card_last4,
                'citi_access_token': instance.citi_access_token,
                'citi_token_type': instance.citi_token_type,
                "citi_order_id": instance.citi_order_id,
            }
            return data_to_update
        else:
            logger.info(
                "Transaction object not found for payment reference "
                "{}".format(payment_reference))
            return None
    except Exception as e:
        logger.error("Error while preparing data for youpay transaction "
                     "update {}".format(e), exc_info=True)
