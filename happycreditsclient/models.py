import uuid

from django.db import models

from core.models import AbstractDateTime
from core.validators import DecimalValidator
from .constants import (HAPPY_CREDITS_STATUS_CHOICE,
                        HAPPY_CREDITS_STATUS_PENDING)


class HappyCreditsClientData(AbstractDateTime):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False,
                                      unique=True)
    customer_email = models.CharField(max_length=500, db_index=True)
    request_data = models.JSONField(
        null=True, blank=True, help_text="used to store webhook request data")
    payment_reference = models.CharField(
        max_length=120, blank=False, db_index=True,
        help_text='Payment reference number')
    available_credit_balance = models.DecimalField(
        decimal_places=4, max_digits=12, null=True, blank=True,
        validators=[DecimalValidator(12, 4)],
        help_text="used to store happy credits user balance amount "
                  "after deduction in amount currency")
    status = models.CharField(max_length=200, db_index=True,
                              choices=HAPPY_CREDITS_STATUS_CHOICE,
                              default=HAPPY_CREDITS_STATUS_PENDING,
                              help_text='Payment status')

    def __str__(self):
        return self.payment_reference
