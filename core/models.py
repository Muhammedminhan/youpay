from django.contrib.auth import get_user_model
from django.db import models

from core.constants import GUEST_USER_OPTIONS
from payments.constants import (PAYMENT_OPTION_CHOICES,
                                PAYMENT_METHOD_MODEL_CHOICES)

# Create your models here.

YOUPAY_TRANSACTION_DATA = 'payments.YouPayTransactionData'

User = get_user_model()


class AbstractDateTime(models.Model):
    created_at = models.DateTimeField(auto_now_add=True,
                                      help_text='Date and time when the '
                                                'payment gateway was created')
    updated_at = models.DateTimeField(auto_now=True,
                                      help_text='Date and time when the '
                                                'payment gateway was updated')

    class Meta:
        abstract = True


class AbstractUserBase(models.Model):
    created_by = models.ForeignKey(User,
                                   related_name='%(class)s_createdby',
                                   on_delete=models.CASCADE,
                                   null=True, blank=True)
    modified_by = models.ForeignKey(User,
                                    related_name='%(class)s_modifiedby',
                                    on_delete=models.CASCADE,
                                    null=True, blank=True)

    class Meta:
        abstract = True


class CustomerProfile(models.Model):
    customer_email = models.EmailField(max_length=255, null=True, blank=True,
                                       help_text="To store user email from "
                                                 "outside")
    customer_phone = models.CharField(max_length=20, null=True, blank=True,
                                      help_text="To store user phone from "
                                                "outside")
    customer_name = models.CharField(max_length=100, null=True, blank=True,
                                     help_text="To store name")

    class Meta:
        abstract = True


class AppConfig(AbstractDateTime, AbstractUserBase):
    front_end_domain = models.CharField(
        max_length=500, null=True, blank=True,
        help_text="Youpay front end domain, ex : https://www.youpay-frontend.com/")
    redirect_path = models.CharField(
        max_length=500, null=True,
        blank=True,
        help_text="verify payment path for youpay, ex : redirect/")


class Currency(AbstractDateTime, AbstractUserBase):
    iso_code = models.CharField(
        max_length=3, unique=True, help_text='ISO 4217 code of the currency')
    name = models.CharField(
        max_length=63)
    decimal_notation = models.PositiveIntegerField(
        null=True, blank=True, default=2,
        help_text='This field denotes the number of decimal points in amount '
                  'for currency displayed. for eg. For AED, the amount is '
                  'always displayed in 3 decimal points. AED 20.456')

    def __str__(self):
        return self.iso_code


class Country(AbstractDateTime, AbstractUserBase):
    name = models.CharField(
        max_length=255, unique=True)
    slug = models.SlugField(
        blank=True)
    pretty_name = models.CharField(
        max_length=255, default='')
    iso_code = models.CharField(
        max_length=6, unique=True, help_text='ISO 3166-1 alpha-2 code for '
                                             'country')
    three_letter_code = models.CharField(
        max_length=3, unique=True, blank=True, null=True,
        help_text='The field is used to defined Countries 3 letter code e.g '
                  'UAE is ARE and etc. You can get the codes from '
                  'http://www.worldatlas.com/aatlas/ctycodes.htm')
    flag = models.ImageField(
        max_length=1024, null=True, blank=True, default=None,
        help_text='Flag of the country')
    timezone = models.CharField(
        max_length=200, help_text='Timezone of the country')
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, blank=False, null=True,
        related_name='country_currency')
    order_number = models.IntegerField(
        default=0)
    is_gcc = models.BooleanField(
        default=False, help_text='This flag determines if the country belongs'
                                 ' to GCC or not')

    def __str__(self):
        return self.iso_code


class PaymentMethod(AbstractDateTime, AbstractUserBase):
    payment_method = models.CharField(
        max_length=100,
        choices=PAYMENT_OPTION_CHOICES,
        help_text='Chosen payment method')
    country = models.ManyToManyField('core.Country', blank=True)
    clients = models.ManyToManyField('services.APIClient', blank=True)
    active = models.BooleanField(
        default=False, help_text='Denotes whether the payment '
                                 'method is active or not')
    guest_user_enabled = models.BooleanField(
        default=False, help_text='Denotes whether the payment method is '
                                 'available for the guest user')
    payment_gateway = models.ForeignKey(
        'integrations.PaymentGateway', on_delete=models.CASCADE,
        blank=True, null=True,
        help_text='Payment gateway for the payment method')

    def __str__(self):
        return self.payment_method


class PaymentConfiguration(AbstractDateTime, AbstractUserBase):
    payment_method = models.CharField(
        max_length=100, db_index=True,
        choices=PAYMENT_METHOD_MODEL_CHOICES,
        help_text='Chosen payment method')
    active = models.BooleanField(
        default=False, db_index=True, help_text='Denotes whether the payment '
                                 'method is active or not')
    guest_user_enabled = models.CharField(
        choices=GUEST_USER_OPTIONS, max_length=200, null=True, db_index=True,
        blank=True)
    payment_gateway = models.ForeignKey(
        'integrations.PaymentGateway', on_delete=models.CASCADE,
        blank=True, null=True, db_index=True,
        help_text='Payment gateway for the payment method')
    partial_redemption_allowed = models.BooleanField(
        default=False, db_index=True,
        help_text='Indicates whether the payment method allows partial '
                  'redemption. Only affects payment methods that support '
                  'partial redemption.')
    burn_full_redemption_enabled = models.BooleanField(
        default=False, db_index=True,
        help_text='Indicates whether full redemption enabled or not')
    earn_enabled = models.BooleanField(
        default=False, db_index=True,
        help_text='Indicates whether earn enabled or not')
    earn_on_partial_redemption = models.BooleanField(
        default=False, db_index=True,
        help_text='Indicates whether earn on partial redemption enabled')

    def __str__(self):
        return self.payment_method


class PaymentMethodConfig(models.Model):
    payment_method = models.ForeignKey(
        'PaymentConfiguration', on_delete=models.CASCADE)
    country = models.ForeignKey(
        'core.Country', on_delete=models.CASCADE)
    client = models.ForeignKey(
        'services.APIClient', on_delete=models.CASCADE)
    active = models.BooleanField(
        default=True, help_text='Denotes whether the payment method '
                                'configuration is active or not')
    guest_user_enabled = models.BooleanField(
        default=True, help_text='Denotes whether the payment method is '
                                'available for the guest user')

    def __str__(self):
        return f"{self.country} - {self.client}"

    class Meta:
        unique_together = ('payment_method', 'country', 'client')
