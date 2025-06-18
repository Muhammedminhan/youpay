import logging

import requests
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from core.models import AbstractDateTime, AbstractUserBase, CustomerProfile
from gateways.paypal.constants import (PAYPAL_STATUS_CHOICES,
                                       PAYPAL_AUTHENTICATION_ENDPOINT,
                                       PAYPAL_EVENT_STATUS_MAPPING)
from services.v1.views.common import get_saved_fields

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
    debug_id = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.CharField(max_length=255, blank=True, null=True)


class PayPalWebhookLog(AbstractDateTime):
    event_id = models.CharField(max_length=128, blank=True, null=True)
    event_type = models.CharField(max_length=128)
    resource_type = models.CharField(max_length=64, null=True, blank=True)
    summary = models.CharField(max_length=500, null=True, blank=True)
    order_id = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=64, null=True, blank=True)
    intent = models.CharField(max_length=64, null=True, blank=True)
    payer_id = models.CharField(max_length=64, null=True, blank=True)
    payer_email = models.EmailField(null=True, blank=True)
    payer_name = models.CharField(max_length=128, null=True, blank=True)
    capture_id = models.CharField(max_length=64, null=True, blank=True)
    capture_status = models.CharField(max_length=64, null=True, blank=True)
    invoice_id = models.CharField(max_length=128, null=True, blank=True)
    payment_reference = models.CharField(max_length=128, null=True,
                                         blank=True)
    amount_value = models.CharField(max_length=32, null=True, blank=True)
    amount_currency = models.CharField(max_length=8, null=True, blank=True)
    paypal_fee = models.CharField(max_length=32, null=True, blank=True)
    net_amount = models.CharField(max_length=32, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.order_id


@receiver(post_save, sender=PayPalWebhookLog)
def update_paypal_transaction(sender, instance, created, **kwargs):
    try:
        data_to_update = prepare_paypal_transaction_update_data(instance)
        payment_reference = instance.payment_reference
        order_id = instance.order_id
        paypal_transaction = get_paypal_transaction(order_id)
        if not paypal_transaction:
            logger.error(
                "PaypalTransaction not found for order_id {}, reference_id {}".format(
                    instance.order_id, instance.payment_reference)
            )
            return

        is_updated = update_paypal_transaction_data(paypal_transaction,
                                                    data_to_update)
        if is_updated:
            logger.info(
                "PaypalTransaction updated for webhook event_id {}, order_id {}".format(
                    instance.event_id, instance.order_id)
            )
        else:
            logger.error(
                "PaypalTransaction not updated for webhook event_id {}, order_id= {}".format(
                    instance.event_id, instance.order_id)
            )
    except Exception as e:
        logger.error(
            "Error syncing PaypalTransaction for webhook {}: {}".format(
                instance.event_id, str(e)))


def prepare_paypal_transaction_update_data(instance):
    status = PAYPAL_EVENT_STATUS_MAPPING.get(instance.event_type)
    update_data = {
        'status': status,
    }
    return update_data


def update_paypal_transaction_data(paypal_transaction,
                                   response_data):
    """Method to update paypal transaction data"""

    data_dict = {}
    try:
        data_dict["status"] = response_data.get("status")

        saved_fields = ["updated_at"]
        saved_fields = get_saved_fields(saved_fields, data_dict,
                                        paypal_transaction)

        paypal_transaction.save(update_fields=saved_fields)

        logger.info(
            "PaypalTransaction updated for order_id {}, status: {}, fields updated: {}".format(
                paypal_transaction.order_id, paypal_transaction.status,
                saved_fields
            )
        )
        return True
    except Exception as e:
        logger.error(
            "Failed to update PaypalTransaction for order_id {}: {}".format(
                paypal_transaction.order_id, e))
        return False


def get_paypal_transaction(order_id):
    with transaction.atomic():
        try:
            return PaypalTransaction.objects.get(order_id=order_id)
        except PaypalTransaction.DoesNotExist:
            logger.error(
                "Paypal transaction not found for order {}".format(
                    order_id))
            return None
