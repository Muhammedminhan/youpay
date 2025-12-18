from django.conf import settings
from rest_framework.permissions import BasePermission


class APIClientRegistrationPermission(BasePermission):

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if settings.ENVIRONMENT == 'qa':
            return True
        else:
            return False
