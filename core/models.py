from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.

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

