import logging
import uuid

from django.core.validators import URLValidator
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save, post_init
from django.dispatch import receiver

from core.constants import (PAYMENT_GATEWAY_CHOICES,
                            PURCHASE_PLATFORM_CHOICES,
                            PAYMENT_REQUEST_LANGUAGE_CHOICES)
from core.exceptions import ClientWebhookFailed
from core.models import AbstractDateTime, CustomerProfile, AbstractUserBase
from core.validators import DecimalValidator
from payments.constants import (
    YOUPAY_TRANSACTION_PAYMENT_STATUS_CHOICES, PAYMENT_METHOD_CHOICES,
    PAYMENT_SCHEME_CHOICES, PAYMENT_SCHEME_NONE,
    PAYMENT_METHOD_NONE, SETTLEMENT_ENTITY_CHOICES)

logger = logging.getLogger(__name__)

SERVICES_APICLIENT = 'services.APIClient'

# Create your models here.


class YouPayTransactionData(AbstractDateTime, CustomerProfile):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False,
                                      db_index=True, unique=True)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 db_index=True,
                                 validators=[DecimalValidator(12, 4)],
                                 help_text="used to store total order amount")
    amount_in_aed = models.DecimalField(decimal_places=4, max_digits=12,
                                        null=True, blank=True,
                                        validators=[DecimalValidator(12, 4)],
                                        help_text="used to store total order"
                                                  " amount converted to AED")
    currency = models.CharField(null=False, blank=False, max_length=15,
                                help_text="used to store currency details",
                                db_index=True)
    country_code = models.CharField(null=True, blank=True, max_length=15,
                                    db_index=True,
                                    help_text="used to store country_code")
    ip = models.CharField(max_length=20, null=True, blank=True)
    invoice_id = models.CharField(max_length=120, null=True, blank=True,
                                  db_index=True)
    order_reference = models.CharField(max_length=120, null=True, blank=True,
                                       db_index=True)
    payment_reference = models.CharField(max_length=120, null=True,
                                         db_index=True, blank=True)
    api_client = models.ForeignKey(SERVICES_APICLIENT, null=True,
                                   db_index=True,
                                   blank=True, on_delete=models.PROTECT)
    service_fee = models.DecimalField(decimal_places=4, max_digits=12,
                                      null=True, blank=True,
                                      validators=[DecimalValidator(12, 4)],
                                      help_text="used to store service fee")
    base_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                      null=True, blank=True,
                                      validators=[DecimalValidator(12, 4)],
                                      help_text="used to store base amount")

    VAT_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                     null=True, blank=True,
                                     validators=[DecimalValidator(12, 4)],
                                     help_text="used to store VAT amount")
    order_history = models.JSONField(null=True, blank=True,
                                     help_text="used to store order history")
    payment_gateway = models.CharField(max_length=20, null=True, blank=True,
                                       db_index=True,
                                       choices=PAYMENT_GATEWAY_CHOICES)
    payment_status = models.CharField(
        max_length=20, null=True, blank=True, db_index=True,
        choices=YOUPAY_TRANSACTION_PAYMENT_STATUS_CHOICES)
    session_id = models.CharField(max_length=500, null=True, blank=True)
    channel_code = models.CharField(
        max_length=120, null=True, blank=True,
        help_text="Channel code used for the transaction, if transaction is"
                  " through checkout")

    is_fraud = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is fraud or not.')
    is_flagged = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is marked as flagged or not.')
    card_bin = models.CharField(
        max_length=6, null=True, blank=True, db_index=True,
        help_text='Denotes the bin number of the card used for the payment')
    card_last4 = models.CharField(max_length=4, null=True, blank=True,
                                  help_text='Denotes the last 4 digits of the'
                                            ' card used for the payment')
    name_on_card = models.CharField(max_length=255, null=True, blank=True,
                                    help_text='Denotes the name on the card')
    payment_method = models.CharField(max_length=200, db_index=True,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      default=PAYMENT_METHOD_NONE,
                                      help_text='Payment Method')
    payment_scheme = models.CharField(
        max_length=200,
        choices=PAYMENT_SCHEME_CHOICES,
        default=PAYMENT_SCHEME_NONE,
        help_text='Denotes the payment scheme used for the payment')

    is_gcc_card = models.BooleanField(
        default=False, db_index=True,
        help_text='Determine whether the transaction is carried out using '
                  'card belongs to GCC country.')

    card_issuer_country = models.CharField(
        max_length=4, null=True, blank=True, db_index=True,
        help_text='Denotes two letter code card issued country.')
    platform = models.CharField(choices=PURCHASE_PLATFORM_CHOICES,
                                max_length=200, null=True, blank=True,
                                help_text="to identify the platform")
    response_summary = models.CharField(
        max_length=500, null=True, blank=True,
        help_text='Checkout response summary text')
    approved = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is approved or not')

    success_url = models.CharField(
        max_length=500, blank=True, db_index=True,
        help_text='Success URL, example :http://www.example.com/success/',
        validators=[URLValidator()])
    failure_url = models.CharField(
        max_length=500, blank=True, db_index=True,
        help_text='Failure URL, example :http://www.example.com/failure/',
        validators=[URLValidator()])
    cancel_url = models.CharField(
        max_length=500, blank=True, db_index=True,
        help_text='Cancel URL, example :http://www.example.com/cancel/',
        validators=[URLValidator()])
    verify_url = models.CharField(
        max_length=500, blank=True, db_index=True,
        help_text='Verify URL, example :http://www.example.com/verify/',
        validators=[URLValidator()])

    language = models.CharField(choices=PAYMENT_REQUEST_LANGUAGE_CHOICES,
                                max_length=15, null=True, blank=True,
                                db_index=True,
                                help_text="to identify the language")
    order_items = models.JSONField(null=True, blank=True,
                                   help_text="used to store order history")
    loyalty_level = models.IntegerField(
        null=True, blank=True, default=0,
        help_text="used to store loyalty level")

    # adcb related data
    redeemed_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='amount which is redeemed on ADCB')
    redeemed_points = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='points which is redeemed on ADCB')
    payable_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='amount which is paid using credit/debit card by the'
                  ' customer')
    available_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='Available amount for the card')
    available_points = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='Available points for the card')
    is_full_redemption = models.BooleanField(
        db_index=True, null=True, blank=True,
        help_text='Denotes whether the redemption is full or not.')
    maximum_redeemable_points = models.IntegerField(
        null=True, blank=True, help_text=('Maximum points used for citi '
                                          'rewards point redemption'))
    minimum_redeemable_points = models.IntegerField(
        null=True, blank=True, help_text=('Minimum points used for citi '
                                          'rewards point redemption'))
    amount_conversion_rate = models.DecimalField(
        null=True, blank=True, decimal_places=10, max_digits=12,
        help_text=('Conversion rate received from citi '
                   'rewards point balance api'))
    citi_order_id = models.CharField(
        max_length=300, null=True, blank=True,
        help_text='Order id received from citi rewards redemption api')
    citi_phone_number = models.CharField(
        max_length=20, null=True, blank=True,
        help_text=("To store phone number used to generate "
                   "otp in citi rewards"))
    cart_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                      null=True, blank=True,
                                      validators=[DecimalValidator(12, 4)],
                                      help_text="used to store cart "
                                                "VAT amount")
    cart_currency = models.CharField(null=True, blank=True, max_length=15,
                                     help_text="used to store cart currency "
                                               "details")
    cart_service_fee = models.DecimalField(decimal_places=4, max_digits=12,
                                           null=True, blank=True,
                                           validators=[
                                               DecimalValidator(12, 4)],
                                           help_text="used to store cart "
                                                     "service fee")
    cart_base_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                           null=True, blank=True,
                                           validators=[
                                               DecimalValidator(12, 4)],
                                           help_text="used to store cart "
                                                     "base amount")
    cart_VAT_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                          null=True, blank=True,
                                          validators=[
                                              DecimalValidator(12, 4)],
                                          help_text="used to store cart "
                                                    "VAT amount")
    happy_credit_reference = models.CharField(max_length=120, null=True,
                                         blank=True)
    credit_balance_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store happy credits user balance amount "
                  "in amount currency")
    available_credit_balance = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store happy credits user balance amount "
                  "after deduction in amount currency")
    retry_count = models.IntegerField(default=0, null=True, blank=True,
                                      db_index=True,
                                      help_text="used to store retry count")
    additional_vat_percentage = models.DecimalField(
        default=0.0, decimal_places=2, null=True, blank=True, max_digits=5,
        help_text='Percentage value of VAT')
    additional_currency_decimal_notation = models.FloatField(
        default=0, null=True, blank=True,
        help_text="used to store currency decimal notation")
    additional_vat = models.DecimalField(
        decimal_places=4, max_digits=12,  null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store new vat amount")
    additional_processing_fee = models.DecimalField(
        decimal_places=4, max_digits=12,  null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store calculated processing fee")
    additional_processing_fee_vat = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store vat amount of the processing fee")
    additional_total_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store total amount after processing fee "
                  "calculation")
    gateway_charge = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="Used to store calculated gateway charges "
                  "based on the configuration")
    settlement_entity = models.CharField(
        max_length=100, null=True, blank=True,
        choices=SETTLEMENT_ENTITY_CHOICES,
        help_text="used to store settlement entity")
    is_guest = models.BooleanField(
        default=False, db_index=True,
        help_text='Denotes whether the payment is done by guest user or not.')
    is_payment_verified = models.BooleanField(
        default=False, db_index=True,
        help_text='Flag to manage duplicate verification.')
    qitaf_phone_number = models.CharField(max_length=20, null=True,
                                          blank=True, db_index=True,
                                          help_text="To store user qitaf "
                                                    "phone number")
    is_qitaf_enabled = models.BooleanField(null=True, blank=True,
                                           default=False, db_index=True,
                                           help_text='Qitaf enabled flag')
    qitaf_request_id = models.CharField(max_length=100, null=True,
                                        blank=True, db_index=True,
                                        help_text='Request id generated by Qitaf')
    earned_point = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='Earned point for the transaction via corresponding payment'
                  ' method')

@receiver(post_init, sender=YouPayTransactionData)
def set_previous_status(sender, instance, **kwargs):
    instance.previous_status = instance.payment_status


@receiver(post_save, sender=YouPayTransactionData)
def update_client(sender, instance, created, **kwargs):
    """
    Signal to send webhook for client on each transaction
    """
    try:
        from services.v1.views.client_webhook import ClientService
        service = ClientService()
        payment_transaction = YouPayTransactionData.objects.get(
            id=instance.id)

        if instance.previous_status != instance.payment_status:
            # logger for youpay status update
            logger.info(
                "Payment status updated for transaction ({}) : {} --> {}"
                "".format(instance.transaction_id,
                          instance.previous_status,
                          instance.payment_status))

        transaction.on_commit(
            lambda: service.webhook_service(payment_transaction))

    except ClientWebhookFailed as e:
        logger.error("Exception occurred  {} on send webhook to client for "
                     "{}, ".format(str(e), instance.transaction_id))

    except Exception as e:
        logger.error("Exception occurred  {} on signal update_client for "
                     "{}, ".format(str(e), instance.transaction_id))


class Announcement(AbstractDateTime, AbstractUserBase):
    gateway = models.ForeignKey('integrations.PaymentGateway', null=True,
                                blank=True, on_delete=models.CASCADE,
                                related_name="gateway_announcement")
    offer_message = models.TextField(null=True, blank=True,
                                     help_text='Announcement message')
    offer_message_arabic = models.TextField(null=True, blank=True,
                                            help_text='Announcement message '
                                                      'in arabic')
    is_active = models.BooleanField(default=False,
                                    help_text='Determines whether the '
                                              'announcement is active or not.')
    platform = models.CharField(choices=PURCHASE_PLATFORM_CHOICES,
                                max_length=200, null=True, blank=True,
                                help_text="Associated platform")
    payment_option = models.ForeignKey('integrations.PaymentOptions',
                                       null=True, blank=True,
                                       on_delete=models.CASCADE,
                                       related_name=
                                       'payment_option_announcement')

    def __str__(self):
        return str(self.gateway)


class ClientNotification(AbstractDateTime):
    transaction = models.ForeignKey('payments.YouPayTransactionData',
                                    null=True, blank=True,
                                    on_delete=models.CASCADE, help_text=
                                    'Associated transaction',
                                    related_name=
                                    "transaction_clientnotification")
    api_client = models.ForeignKey(SERVICES_APICLIENT, null=True,
                                   blank=True, on_delete=models.CASCADE,
                                   help_text='Related api client')
    event_type = models.CharField(max_length=100, null=True, blank=True,
                                  help_text='Name of the notification event')
    is_notified = models.BooleanField(default=False, db_index=True,
                                      help_text='Denotes whether the webhook '
                                                'is received at client end or '
                                                'not')
    notification_response_status = models.BooleanField(default=False,
                                                       db_index=True,
                                                       help_text=
                                                       'Denotes webhook '
                                                       'notification is '
                                                       'successful or not')
    retries_count = models.IntegerField(default=0,
                                        help_text='Denotes webhook '
                                                  'notification retries, '
                                                  'how many time it is'
                                                  ' retried')
    payment_status = models.CharField(max_length=100, null=True, blank=True,
                                      help_text='payment transaction status')

    def __str__(self):
        return str(self.transaction.transaction_id)


class AdditionalCharge(AbstractDateTime):
    transaction = models.ForeignKey(
        'payments.YouPayTransactionData', null=True, blank=True,
        on_delete=models.CASCADE, related_name="payment_transaction"
    )
    payment_option = models.CharField(max_length=255,  null=True, blank=True,
                                      help_text='Name of the payment option')
    additional_vat = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store new vat amount")
    additional_processing_fee = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store calculated processing fee")
    additional_processing_fee_vat = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store vat amount of the processing fee")
    additional_total_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store total amount after processing fee "
                  "calculation")

    def __str__(self):
        return str(self.transaction_id)


class ArchivedYouPayTransactionData(models.Model):
    customer_email = models.CharField(max_length=255, null=True, blank=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_name = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(help_text='Date and time when the '
                                                'payment was created')
    updated_at = models.DateTimeField(help_text='Date and time when the '
                                                'payment was updated')
    archived_at = models.DateTimeField(auto_now=True,
                                       help_text='Date and time when the last'
                                                 ' payment was archived')

    transaction_id = models.CharField(null=True, blank=True, max_length=100)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 db_index=True)
    currency = models.CharField(null=False, blank=False, max_length=15,
                                db_index=True)
    country_code = models.CharField(null=True, blank=True, max_length=15,
                                    db_index=True)
    ip = models.CharField(max_length=20, null=True, blank=True)
    invoice_id = models.CharField(max_length=120, null=True, blank=True,
                                  db_index=True)
    order_reference = models.CharField(max_length=120, null=True, blank=True,
                                       db_index=True)
    payment_reference = models.CharField(max_length=120, null=True,
                                         db_index=True, blank=True)
    api_client = models.ForeignKey(SERVICES_APICLIENT, null=True,
                                   db_index=True,
                                   blank=True, on_delete=models.PROTECT)
    service_fee = models.DecimalField(decimal_places=4, max_digits=12,
                                      null=True, blank=True)
    base_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                      null=True, blank=True)

    VAT_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                     null=True, blank=True)
    order_history = models.JSONField(null=True, blank=True)
    payment_gateway = models.CharField(max_length=20, null=True, blank=True,
                                       db_index=True,
                                       choices=PAYMENT_GATEWAY_CHOICES)
    payment_status = models.CharField(
        max_length=20, null=True, blank=True, db_index=True,
        choices=YOUPAY_TRANSACTION_PAYMENT_STATUS_CHOICES)
    session_id = models.CharField(max_length=500, null=True, blank=True)
    channel_code = models.CharField(
        max_length=120, null=True, blank=True)

    is_fraud = models.BooleanField(default=False, db_index=True)
    is_flagged = models.BooleanField(default=False, db_index=True)
    card_bin = models.CharField(max_length=6, null=True, blank=True,
                                db_index=True)
    card_last4 = models.CharField(max_length=4, null=True, blank=True)
    name_on_card = models.CharField(max_length=255, null=True, blank=True)
    payment_method = models.CharField(max_length=200, db_index=True,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      default=PAYMENT_METHOD_NONE,
                                      help_text='Payment Method')
    payment_scheme = models.CharField(max_length=200,
                                      choices=PAYMENT_SCHEME_CHOICES,
                                      default=PAYMENT_SCHEME_NONE)

    is_gcc_card = models.BooleanField(default=False, db_index=True)

    card_issuer_country = models.CharField(max_length=4, null=True,
                                           blank=True, db_index=True)
    platform = models.CharField(choices=PURCHASE_PLATFORM_CHOICES,
                                max_length=200, null=True, blank=True)
    response_summary = models.CharField(max_length=500, null=True, blank=True)
    approved = models.BooleanField(default=False, db_index=True)

    success_url = models.CharField(max_length=500, blank=True, db_index=True)
    failure_url = models.CharField(max_length=500, blank=True, db_index=True)
    cancel_url = models.CharField(max_length=500, blank=True, db_index=True)
    verify_url = models.CharField(max_length=500, blank=True, db_index=True)

    language = models.CharField(choices=PAYMENT_REQUEST_LANGUAGE_CHOICES,
                                max_length=15, null=True, blank=True,
                                db_index=True)
    order_items = models.JSONField(null=True, blank=True)
    loyalty_level = models.IntegerField(null=True, blank=True, default=0)

    # adcb related data
    redeemed_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    redeemed_points = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    payable_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    available_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    available_points = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    is_full_redemption = models.BooleanField(
        db_index=True, null=True, blank=True)
    maximum_redeemable_points = models.IntegerField(
        null=True, blank=True)
    minimum_redeemable_points = models.IntegerField(
        null=True, blank=True)
    amount_conversion_rate = models.DecimalField(
        null=True, blank=True, decimal_places=10, max_digits=12)
    citi_order_id = models.CharField(
        max_length=300, null=True, blank=True)
    citi_phone_number = models.CharField(
        max_length=20, null=True, blank=True)

    cart_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                      null=True, blank=True)
    cart_currency = models.CharField(null=True, blank=True, max_length=15)
    cart_service_fee = models.DecimalField(decimal_places=4, max_digits=12,
                                           null=True, blank=True)
    cart_base_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                           null=True, blank=True)
    cart_VAT_amount = models.DecimalField(decimal_places=4, max_digits=12,
                                          null=True, blank=True)
    happy_credit_reference = models.CharField(max_length=120, null=True,
                                              blank=True)
    credit_balance_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    available_credit_balance = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    retry_count = models.IntegerField(default=0, null=True, blank=True,
                                      db_index=True)
    additional_vat_percentage = models.DecimalField(
        default=0.0, decimal_places=2, null=True, blank=True, max_digits=5)
    additional_currency_decimal_notation = models.FloatField(
        default=0, null=True, blank=True)
    additional_vat = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True, )
    additional_processing_fee = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    additional_processing_fee_vat = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    additional_total_amount = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    gateway_charge = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True)
    settlement_entity = models.CharField(
        max_length=100, null=True, blank=True,
        choices=SETTLEMENT_ENTITY_CHOICES)
    is_guest = models.BooleanField(default=False, db_index=True)
    is_payment_verified = models.BooleanField(default=False, db_index=True)
    amount_in_aed = models.DecimalField(decimal_places=4, max_digits=12,
                                        null=True, blank=True, db_index=True)
    qitaf_phone_number = models.CharField(max_length=20, null=True,
                                          blank=True, db_index=True)
    is_qitaf_enabled = models.BooleanField(default=False, db_index=True, )
    qitaf_request_id = models.CharField(max_length=100, null=True,
                                        blank=True, db_index=True,
                                        help_text='Request id generated by Qitaf')
    earned_point = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        help_text='Earned point for the transaction via corresponding payment'
                  ' method')
