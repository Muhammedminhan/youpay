import logging

from rest_framework import authentication
from rest_framework import exceptions

from integrations.constants import TABBYPG_HUB_CODE
from services.v1.views.common import get_api_key_from_payment_gateway

logger = logging.getLogger(__name__)


class SignatureAuthentication(authentication.BaseAuthentication):
    API_KEY_HEADER = 'X-Api-Key'

    def header_canonical(self, header_name):
        """Translate HTTP headers to Django header names."""
        # Translate as stated in the docs:
        # https://docs.djangoproject.com/en/1.6/ref/request-response/#django.http.HttpRequest.META
        header_name = header_name.lower()
        if header_name == 'content-type':
            return 'CONTENT-TYPE'
        elif header_name == 'content-length':
            return 'CONTENT-LENGTH'
        return 'HTTP_%s' % header_name.replace('-', '_').upper()

    def fetch_user_data(self, api_key):
        """Returns (User instance, API Secret) or None if api_key is bad."""
        try:
            client_api_key = get_api_key_from_payment_gateway(
                TABBYPG_HUB_CODE)
            return client_api_key

        except Exception as e:
            logger.info("Exception in fetch_user_data: {}".format(e))
            return None

    def authenticate(self, request):
        # Check for API key header.
        logger.info("Triggered in authenticate")
        user = None
        api_key_header = self.header_canonical(self.API_KEY_HEADER)
        api_key = request.META.get(api_key_header)
        if not api_key:
            logger.info("Authentication failed due to api key not exists")
            return None
        client_api_key = self.fetch_user_data(api_key)
        if client_api_key != api_key:
            logger.info(
                "API key :'{}', and client api key :'{}', not matching"
                "".format(api_key, client_api_key))
            raise exceptions.AuthenticationFailed('Bad signature')

        return (user, api_key)
