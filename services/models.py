import hashlib
import secrets

from django.db import models

from core.constants import (
    PURCHASE_PLATFORM_CHOICES,
    PAYMENT_REQUEST_LANGUAGE_CHOICES)
from core.models import AbstractDateTime, AbstractUserBase, CustomerProfile
from core.validators import DecimalValidator, MinLengthValidator, URLValidator


# Create your models here.
class APIClient(AbstractDateTime, AbstractUserBase):
    name = models.CharField(null=False, blank=True, max_length=100,
                            help_text='Name of the API Client')
    api_key = models.CharField(max_length=100, blank=True,
                               help_text='API Key',
                               validators=[MinLengthValidator(20)],
                               unique=True)
    is_active = models.BooleanField(default=False,
                                    help_text='Denotes whether the API '
                                              'Client is active or not')
    webhook_url = models.CharField(max_length=500, blank=True,
                                   help_text='Webhook URL',
                                   validators=[URLValidator()])

    success_url = models.CharField(max_length=500, blank=True,
                                   help_text='Success URL',
                                   validators=[URLValidator()])
    failure_url = models.CharField(max_length=500, blank=True,
                                   help_text='Failure URL',
                                   validators=[URLValidator()])
    cancel_url = models.CharField(max_length=500, blank=True,
                                  help_text='Cancel URL',
                                  validators=[URLValidator()])
    verify_url = models.CharField(max_length=500, blank=True,
                                  help_text='Verify URL',
                                  validators=[URLValidator()])
    client_domain = models.CharField(null=True, blank=True, max_length=100,
                                     help_text='Client Domain, example : '
                                               'https://google.com/')
    logo_file = models.ImageField(upload_to='logo_files', blank=True,
                                  null=True, help_text='Logo for the client')
    color_code = models.CharField(max_length=20, blank=True, null=True,
                                  validators=[MinLengthValidator(4)],
                                  help_text='Color code for the client')
    client_code = models.CharField(max_length=100, blank=True, null=True,
                                   help_text='Client Code')
    payment_gateway = models.ManyToManyField('integrations.PaymentGateway',
                                             blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe()
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
