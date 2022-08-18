from django.db import models

from core.models import AbstractDateTime, AbstractUserBase
from core.validators import MinLengthValidator, URLValidator


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
                                             null=True, blank=True)

    def __str__(self):
        return self.name
