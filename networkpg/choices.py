from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentStatus(models.TextChoices):
    """
    Choices for payment status in Network International.
    """
    PENDING = "PENDING", _("Pending")
    INITIATED = "INITIATED", _("Initiated")
    AUTHORIZED = "AUTHORIZED", _("Authorized")
    CAPTURED = "CAPTURED", _("Captured")
    VOIDED = "VOIDED", _("Voided")
    REFUNDED = "REFUNDED", _("Refunded")
    FAILED = "FAILED", _("Failed")
    DECLINED = "DECLINED", _("Declined")
    PURCHASED = "PURCHASED", _("Purchased")


class OrderAction(models.TextChoices):
    """
    Choices for order actions in Network International.
    """
    AUTH = "AUTH", _("Authorization")
    SALE = "SALE", _("Sale/Purchase")
    CAPTURE = "CAPTURE", _("Capture")
    REFUND = "REFUND", _("Refund")
    VOID = "VOID", _("Void")
