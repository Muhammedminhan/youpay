from django.db import models

from core.models import AbstractUserBase, AbstractDateTime
from notifications.constants import EMAIL_TYPES


# Create your models here.

class EmailTemplateConfiguration(AbstractDateTime, AbstractUserBase):
    """
    configure the email template code from mail engine.
    Note : Before adding new template code add the email type in
    configurations/utils/constant.py,
    """
    email_type = models.CharField(
        max_length=25, choices=EMAIL_TYPES, null=True, blank=True,
        verbose_name='EmailType', help_text="Email type, eg:feedback email")
    template_code = models.CharField(
        max_length=10, null=True, blank=True,
        help_text="email template code from mail engine, eg:ASED78S")
    is_active = models.BooleanField(
        null=False, default=True,
        help_text="whether template code is active or not")
    endpoint_url = models.CharField(
        max_length=500, null=True, blank=True,
        help_text="Mail engine api end point to send mail")

    def __str__(self):
        return str(self.email_type)