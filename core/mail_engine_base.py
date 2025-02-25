import datetime
import logging

import requests
from django.conf import settings
from httpsig.requests_auth import HTTPSignatureAuth

logger = logging.getLogger(__name__)


class MailEngineClient(object):
    """
    Interface into the Ygag MailEngine API
    """
    resource_conflict = 'RESOURCE_CONFLICT'

    def __init__(self):
        self.api_key = settings.MAIL_ENGINE_API_KEY
        self.api_secret = settings.MAIL_ENGINE_API_SECRET
        if not (self.api_key or self.api_secret):
            raise ValueError('Mail Engine API credentials is '
                             'missing or Invalid')

    def get_headers(self):
        """
        form headers for signing
        """
        headers = {
            'Accept': 'application/json',
            'X-Api-Key': self.api_key,
            'date': str(datetime.datetime.utcnow()),
        }
        return headers

    def get_signature_auth(self):
        """
        It returns the authenticated signature.
        :return auth: authentication object
        """
        signature_headers = ['accept', 'date']
        auth = HTTPSignatureAuth(key_id=self.api_key,
                                 secret=self.api_secret,
                                 headers=signature_headers)
        return auth

    def service_post(self, uri, payload=None):
        """
        :param uri: API resource uri
        :param payload: post data send to api end point
        :return: Json response returned from request post
        """
        result = None
        try:
            signature_auth = self.get_signature_auth()
            headers = self.get_headers()
            response = requests.post(
                uri, json=payload, auth=signature_auth, headers=headers)
        except Exception as e:
            logger.error("Error in mail engine request api with payload:"
                         " {} error: {} :".format(payload, str(e)))
            response = None

        if response and response.status_code == 200:
            result = response.json()

        try:
            if response.status_code == 409:
                result = self.resource_conflict
            elif response.status_code != 200:
                result = response.json()
                logger.error("Error in mail engine api response for "
                             "payload: {} response: {}"
                             "".format(payload, response.json()))
        except Exception as e:
            logger.error("Error in mail engine api response for "
                         "payload: {} response: {}".format(payload, str(e)))

        return result
