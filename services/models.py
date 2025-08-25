import hashlib
import secrets

from django.db import models

from core.constants import (
    PURCHASE_PLATFORM_CHOICES,
    PAYMENT_REQUEST_LANGUAGE_CHOICES)
from core.models import (AbstractDateTime, AbstractUserBase, CustomerProfile,
                         Currency)
from core.validators import (DecimalValidator, MinLengthValidator,
                             URLValidator, validate_svg_or_image
                             )


# Create your models here.
class APIClient(AbstractDateTime, AbstractUserBase):
    name = models.CharField(
        null=False, blank=True, max_length=100,
        help_text='Name of the API Client')
    api_key = models.CharField(
        max_length=100, blank=True, help_text='Client API Key',
        validators=[MinLengthValidator(20)], unique=True)
    api_secret = models.CharField(
        max_length=100, blank=True, validators=[MinLengthValidator(20)])
    is_active = models.BooleanField(
        default=False,
        help_text='Denotes whether the API Client is active or not')
    webhook_url = models.CharField(
        max_length=500, blank=True,
        help_text='Webhook URL, example https://youpay-api-client-domain.com/'
                  'youpay/api/v1/webhook/',
        validators=[URLValidator()])
    client_domain = models.CharField(
        null=True, blank=True, max_length=100,
        help_text='Client Domain, '
                  'example :  https://youpay-api-client-domain.com/')
    brand_details_path = models.CharField(
        null=True, blank=True, max_length=100,
        help_text='path to fetch Brand details, example :  brand-details/')
    logo_file = models.FileField(
        upload_to='logo_files', blank=True, null=True,
        validators=[validate_svg_or_image],
        help_text='Logo for the client. Note that the max height, width of '
                  'the logo should be 60px and the file size has to be below 4MB.'
    )
    mobile_logo_file = models.FileField(
        upload_to='mobile_logo_file', blank=True, null=True,
        validators=[validate_svg_or_image],
        help_text='Mobile logo for the client. Note that the max height, '
                  'width of the logo should be 60px and the file size has to '
                  'be below 4MB.')
    color_code = models.CharField(
        max_length=20, blank=True, null=True,
        validators=[MinLengthValidator(4)],
        help_text='Color code for the client in hex')
    client_code = models.CharField(
        max_length=100, blank=True, null=True, help_text='Client Code')
    payment_gateway = models.ManyToManyField(
        'integrations.PaymentGateway', blank=True)
    validate_session = models.BooleanField(
        default=False,
        help_text='Denotes whether the API Client session validation is'
                  ' enabled or not')
    allow_aed_converted_amount = models.BooleanField(
        default=False, help_text='For enabling AED converted amount for the '
                                 'client')
    checkout_channel_code = models.JSONField(
        null=True, blank=True,
        help_text="channel code used by client")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe()
        if not self.api_secret:
            result = hashlib.sha256(self.api_key.encode())
            self.api_secret = result.hexdigest()

        super(APIClient, self).save(*args, **kwargs)


class PaymentRequestData(AbstractDateTime, CustomerProfile):
    request_data = models.JSONField(null=False, blank=False,
                                    help_text="used to store request data")
    response_data = models.JSONField(null=True, blank=True,
                                     help_text="used to store response data")
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 validators=[DecimalValidator(12, 4)],
                                 help_text="used to store total order amount")
    currency = models.CharField(null=False, blank=False, max_length=15,
                                help_text="used to store currency details")
    api_client = models.ForeignKey('services.APIClient', null=True,
                                   blank=True,
                                   on_delete=models.PROTECT)
    invoice_id = models.CharField(max_length=120, null=True, blank=True,
                                  help_text="used to store invoice_id")
    order_reference = models.CharField(
        max_length=120, null=True, blank=True,
        help_text="used to store order_reference")
    payment_reference = models.CharField(
        max_length=120, null=True, blank=True,
        help_text="used to store order_reference")
    platform = models.CharField(choices=PURCHASE_PLATFORM_CHOICES,
                                max_length=200, null=True, blank=True,
                                help_text="to identify the platform")
    language = models.CharField(choices=PAYMENT_REQUEST_LANGUAGE_CHOICES,
                                max_length=15, null=True, blank=True,
                                help_text="to identify the language")

    def __str__(self):
        return self.api_client.name


class ConfigurationData(AbstractDateTime):
    request_data = models.JSONField(null=True, blank=True,
                                    help_text="used to store request data")
    response_data = models.JSONField(null=False, blank=False,
                                     help_text="used to store response data")
    currency = models.ForeignKey(Currency, null=False, blank=False,
                                 on_delete=models.CASCADE,
                                 related_name="configuration_data_currency")
    payment_gateway = models.ForeignKey('integrations.PaymentGateway',
                                        null=False, blank=False,
                                        on_delete=models.PROTECT)
    channel_code = models.CharField(max_length=50, blank=True, null=True,
                                    help_text="For storing channel code - "
                                              "only for checkout")


class OfferDetails(AbstractDateTime):
    invoice_id = models.CharField(max_length=120, null=True, blank=True,
                                  help_text="used to store invoice_id")
    offer_details = models.JSONField(null=True, blank=True,
                                     help_text="used to store offer details")
    client = models.ForeignKey('services.APIClient', null=True, blank=True,
                               on_delete=models.PROTECT)
