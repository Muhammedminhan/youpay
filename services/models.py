import uuid

from django.db import models

from core.constants import (
    PURCHASE_PLATFORM_CHOICES,
    PAYMENT_REQUEST_LANGUAGE_CHOICES,
    YGPay_TRANSACTION_PAYMENT_STATUS_CHOICES)
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
    endpoint_url = models.CharField(max_length=200, blank=True,
                                    help_text='Endpoint URL',
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


class PaymentRequestData(AbstractDateTime, CustomerProfile):
    request_data = models.JSONField(null=False, blank=False,
                                    help_text="used to request data")
    response_data = models.JSONField(null=True, blank=True,
                                     help_text="used to response data")
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 validators=[DecimalValidator(12, 4)],
                                 help_text="used to store total order amount")
    currency = models.CharField(null=False, blank=False, max_length=15,
                                help_text="used to store currency details")
    api_client = models.ForeignKey('services.APIClient', null=True,
                                   blank=True,
                                   on_delete=models.PROTECT)
    invoice = models.CharField(max_length=120, null=True, blank=True)
    order_reference = models.CharField(max_length=120, null=True, blank=True)
    payment_reference = models.CharField(max_length=120, null=True,
                                         blank=True)
    platform = models.CharField(choices=PURCHASE_PLATFORM_CHOICES,
                                max_length=200, null=True, blank=True)
    language = models.CharField(choices=PAYMENT_REQUEST_LANGUAGE_CHOICES,
                                max_length=15, null=True, blank=True)

    def __str__(self):
        return self.api_client.name


#  TODO move to payments create if not exists
class YGPayTransactionData(AbstractDateTime, CustomerProfile):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False,
                                      unique=True)
    amount = models.DecimalField(decimal_places=4, max_digits=12,
                                 validators=[DecimalValidator(12, 4)],
                                 help_text="used to store total order amount")
    currency = models.CharField(null=False, blank=False, max_length=15,
                                help_text="used to store currency details")
    ip = models.CharField(max_length=20, null=True, blank=True)
    invoice = models.CharField(max_length=120, null=True, blank=True)
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
    # TODO choice filed as static gateway value
    payment_gateway = models.ForeignKey('integrations.PaymentGateway',
                                        on_delete=models.PROTECT,
                                        null=True, blank=True)
    payment_status = models.CharField(
        max_length=20, null=True, blank=True,
        choices=YGPay_TRANSACTION_PAYMENT_STATUS_CHOICES)
