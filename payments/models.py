import uuid

from django.core.validators import URLValidator
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.constants import (PAYMENT_GATEWAY_CHOICES,
                            PURCHASE_PLATFORM_CHOICES,
                            PAYMENT_REQUEST_LANGUAGE_CHOICES)
from core.models import AbstractDateTime, CustomerProfile, AbstractUserBase
from core.validators import DecimalValidator
from payments.constants import (
    YOUPAY_TRANSACTION_PAYMENT_STATUS_CHOICES, PAYMENT_METHOD_CHOICES,
    PAYMENT_SCHEME_CHOICES, PAYMENT_SCHEME_NONE,
    PAYMENT_METHOD_NONE)


# Create your models here.


class YouPayTransactionData(AbstractDateTime, CustomerProfile):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False,
                                      unique=True)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 validators=[DecimalValidator(12, 4)],
                                 help_text="used to store total order amount")
    currency = models.CharField(null=False, blank=False, max_length=15,
                                help_text="used to store currency details")
    ip = models.CharField(max_length=20, null=True, blank=True)
    invoice_id = models.CharField(max_length=120, null=True, blank=True)
    order_reference = models.CharField(max_length=120, null=True, blank=True)
    payment_reference = models.CharField(max_length=120, null=True,
                                         blank=True)
    api_client = models.ForeignKey('services.APIClient', null=True,
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
                                       choices=PAYMENT_GATEWAY_CHOICES)
    payment_status = models.CharField(
        max_length=20, null=True, blank=True,
        choices=YOUPAY_TRANSACTION_PAYMENT_STATUS_CHOICES)
    session_id = models.CharField(max_length=500, null=True, blank=True)
    channel_code = models.CharField(
        max_length=120, null=True, blank=True,
        help_text="Channel code used for the transaction, if transaction is"
                  " through checkout")

    is_fraud = models.BooleanField(
        default=False,
        help_text='Denotes whether the payment is fraud or not.')
    is_flagged = models.BooleanField(
        default=False,
        help_text='Denotes whether the payment is marked as flagged or not.')
    card_bin = models.CharField(
        max_length=6, null=True, blank=True,
        help_text='Denotes the bin number of the card used for the payment')
    card_last4 = models.CharField(max_length=4, null=True, blank=True,

                                  help_text='Denotes the last 4 digits of the'
                                            ' card used for the payment')
    name_on_card = models.CharField(max_length=255, null=True, blank=True,
                                    help_text='Denotes the name on the card')
    payment_method = models.CharField(max_length=200,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      default=PAYMENT_METHOD_NONE,
                                      help_text='Payment Method')
    payment_scheme = models.CharField(
        max_length=200,
        choices=PAYMENT_SCHEME_CHOICES,
        default=PAYMENT_SCHEME_NONE,
        help_text='Denotes the payment scheme used for the payment')

    is_gcc_card = models.BooleanField(
        default=False,
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
        default=False,
        help_text='Denotes whether the payment is approved or not')

    success_url = models.CharField(
        max_length=500, blank=True,
        help_text='Success URL, example :http://www.example.com/success/',
        validators=[URLValidator()])
    failure_url = models.CharField(
        max_length=500, blank=True,
        help_text='Failure URL, example :http://www.example.com/failure/',
        validators=[URLValidator()])
    cancel_url = models.CharField(
        max_length=500, blank=True,
        help_text='Cancel URL, example :http://www.example.com/cancel/',
        validators=[URLValidator()])
    verify_url = models.CharField(
        max_length=500, blank=True,
        help_text='Verify URL, example :http://www.example.com/verify/',
        validators=[URLValidator()])

    language = models.CharField(choices=PAYMENT_REQUEST_LANGUAGE_CHOICES,
                                max_length=15, null=True, blank=True,
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


@receiver(post_save, sender=YouPayTransactionData)
def update_client(sender, instance, **kwargs):
    """
    Signal to send webhook for client on each transaction
    """
    from services.v1.views.client_webhook import ClientService
    service = ClientService()
    payment_transaction = YouPayTransactionData.objects.get(
        id=instance.id)
    transaction.on_commit(
        lambda: service.webhook_service(payment_transaction))


class Announcement(AbstractDateTime, AbstractUserBase):
    gateway = models.ForeignKey('integrations.PaymentGateway', null=True,
                                blank=True, on_delete=models.CASCADE,
                                related_name="gateway_announcement")
    offer_message = models.TextField(null=True, blank=True,
                                     help_text='Announcement message')
    is_active = models.BooleanField(default=False, help_text='Determines '
                                                             'whether the announcement is active or not.')

    def __str__(self):
        return str(self.gateway)


class ClientNotification(AbstractDateTime):
    transaction = models.ForeignKey('payments.YouPayTransactionData',
                                    null=True, blank=True,
                                    on_delete=models.CASCADE, help_text=
                                    'Associated transaction',
                                    related_name=
                                    "transaction_clientnotification")
    api_client = models.ForeignKey('services.APIClient', null=True,
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
