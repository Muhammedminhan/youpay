import logging

import requests
from django.db import models
from django.utils import timezone

from core.models import AbstractDateTime, AbstractUserBase, CustomerProfile
from gateways.paypal.constants import (PAYPAL_STATUS_CHOICES,
                                       PAYPAL_AUTHENTICATION_ENDPOINT)

logger = logging.getLogger(__name__)


class PaymentAccessToken(AbstractDateTime):
    access_token = models.CharField(max_length=255)
    expires_in = models.IntegerField()
    token_type = models.CharField(max_length=255, default='Bearer')

    def is_expired(self):
        expiry_time = self.created_at + timezone.timedelta(
            seconds=self.expires_in - 60)
        return timezone.now() > expiry_time

    @classmethod
    def get_paypal_access_token(cls, gateway_obj):
        try:
            token_obj = cls.objects.first()
            if token_obj and not token_obj.is_expired():
                return token_obj.access_token

            logger.info("Access token expired, getting new token")
            url = gateway_obj.domain + PAYPAL_AUTHENTICATION_ENDPOINT

            client_id = gateway_obj.api_key
            client_secret = gateway_obj.api_secret
            response = requests.post(
                url,
                auth=(client_id, client_secret),
                headers={'Accept': 'application/json',
                         'Accept-Language': 'en_US'},
                data={'grant_type': 'client_credentials'}
            )
            data = response.json()

            if response.status_code == 200 and 'access_token' in data:
                access_token = data['access_token']
                expires_in = data.get('expires_in', 3600)

                if token_obj:
                    token_obj.access_token = access_token
                    token_obj.expires_in = expires_in
                    token_obj.created_at = timezone.now()
                    token_obj.save()
                else:
                    token_obj = cls.objects.create(
                        access_token=access_token,
                        expires_in=expires_in,
                    )
                return access_token
            else:
                logger.error("Unable to get paypal access token")
        except Exception as e:
            logger.error("Exception while getting PayPal access token",
                         exc_info=True)


class PaypalTransaction(AbstractDateTime, AbstractUserBase, CustomerProfile):
    order_id = models.CharField(max_length=100, unique=True)
    payment_reference = models.CharField(max_length=100, blank=True,
                                         null=True)
    status = models.CharField(max_length=50, blank=True, null=True,
                              choices=PAYPAL_STATUS_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    capture_id = models.CharField(max_length=100, blank=True, null=True)
    payer_id = models.CharField(max_length=100, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)
    refund_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_fee = models.DecimalField(max_digits=15, decimal_places=3,
                                     blank=True, null=True)
    net_amount = models.DecimalField(max_digits=15, decimal_places=3,
                                     blank=True, null=True)
