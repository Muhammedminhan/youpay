from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.
from core.constants import (PAYMENT_REQUEST_TYPE_CHOICES,
                            PAYMENT_REQUEST_TYPE_NONE, REQUEST_METHOD_CHOICES,
                            REQUEST_METHOD_NONE)

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
    customer_name = models.CharField(max_length=20, null=True, blank=True,
                                     help_text="To store name")

    class Meta:
        abstract = True


class AppConfig(AbstractDateTime, AbstractUserBase):
    front_end_domain = models.CharField(
        max_length=500, null=True, blank=True,
        help_text="front-end domain for the"
                  " redirection from the product")
    front_end_redirect_url = models.CharField(
        max_length=500, null=True,
        blank=True,
        help_text="front-end url for the"
                  " redirection from the gateway")


class YoupayToPaymentGatewaysData(AbstractDateTime):
    youpay_payment = models.ForeignKey(
        YOUPAY_TRANSACTION_DATA,
        on_delete=models.CASCADE,
        blank=False, null=True,
        help_text='Payment'
    )
    request_method = models.CharField(
        max_length=10, null=True, blank=True, choices=REQUEST_METHOD_CHOICES,
        default=PAYMENT_REQUEST_TYPE_NONE, )
    payment_request_data = models.JSONField(
        null=True, blank=True,
        help_text='Payment API request data to client')
    payment_response_data = models.JSONField(
        null=True, blank=True,
        help_text='Payment API response data to client')
    request_type = models.CharField(max_length=200,
                                    choices=PAYMENT_REQUEST_TYPE_CHOICES,
                                    default=REQUEST_METHOD_NONE,
                                    db_index=True,
                                    help_text='Payment status')

    def __str__(self):
        return self.youpay_payment.payment_reference
