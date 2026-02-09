from django.conf import settings
from rest_framework.permissions import BasePermission


class APIClientRegistrationPermission(BasePermission):
    """
    Permission class intended for the API client registration endpoint in the
    `qa` environment
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if settings.ENVIRONMENT == 'qa':
            return True
        else:
            return False
