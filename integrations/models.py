from django.db import models

from core.models import AbstractDateTime, AbstractUserBase

# Create your models here.

PAYMENT_GATEWAY_API_TYPE = [
    ('create', 'Create'),
    ('authorize', 'Authorize'),
    ('verify', 'Verify'),
    ('capture', 'Capture'),
    ('cancell', 'Cancell'),
    ('refund', 'Refund'),
    ('callback', 'Callback'),
    ('close', 'Close'),
]

PAYMENT_REQUEST_METHOD = [
    ('post', 'POST'),
    ('get', 'GET'),
]


class PaymentGateway(AbstractDateTime, AbstractUserBase):
    gateway_name = models.CharField(max_length=255,
                                    help_text='Name of the payment gateway')
    description = models.TextField(null=True, blank=True,
                                   help_text='Description of the payment '
                                             'gateway')
    is_active = models.BooleanField(default=False,
                                    help_text='Denotes whether the payment '
                                              'gateway is active or not')

    domain = models.URLField(max_length=255, blank=True, null=True,
                             help_text='Domain of the payment gateway')
    api_key = models.CharField(max_length=255, blank=True, null=True,
                               help_text='API Key String')
    api_secret = models.CharField(max_length=255, blank=True, null=True,
                                  help_text='API Secret String')

    def __str__(self):
        return self.gateway_name
 

class PaymentGatewayAPI(AbstractDateTime, AbstractUserBase):
    api_name = models.CharField(max_length=255,
                                help_text='Name of the API as Per the Payment '
                                          'Gateway Documentation')
    payment_gateway = models.ForeignKey('integrations.PaymentGateway',
                                        on_delete=models.CASCADE,
                                        help_text='Payment Gateway to which '
                                                  'the API belongs to')
    api_path = models.CharField(max_length=255, blank=False, null=False,
                                help_text='API Path')
    description = models.TextField(null=True, blank=True,
                                   help_text='Description of the API')
    request_method = models.CharField(max_length=255, default='post',
                                      choices=PAYMENT_REQUEST_METHOD,
                                      help_text='Request Method')
    api_type = models.CharField(max_length=255,
                                choices=PAYMENT_GATEWAY_API_TYPE,
                                help_text='API Type in General Format')

    def __str__(self):
        return self.payment_gateway.gateway_name + self.api_name
