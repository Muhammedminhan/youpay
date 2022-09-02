import uuid
from django.db import transaction

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.constants import (
    YGPay_TRANSACTION_PAYMENT_STATUS_CHOICES, PAYMENT_GATEWAY_CHOICES)
from core.models import AbstractDateTime, CustomerProfile
from core.validators import DecimalValidator


# Create your models here.

class YGPayTransactionData(AbstractDateTime, CustomerProfile):
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
        choices=YGPay_TRANSACTION_PAYMENT_STATUS_CHOICES)
    session_id = models.CharField(max_length=120, null=True, blank=True)


@receiver(post_save, sender=YGPayTransactionData, dispatch_uid="update_client")
def update_client(sender, instance, **kwargs):
    print("SIGNAL WORKED FOR CREATE WEBHOOK CLIENT")
    print("sender ",sender)
    print("instance ",instance)
    # from integrations.v1.views.client_service import ClientService
    # service = ClientService()
    # payment_transaction = YGPayTransactionData.objects.get(pk=instance.pk)
    # transaction.on_commit(
    #     lambda: service.webhook_service(payment_transaction))
