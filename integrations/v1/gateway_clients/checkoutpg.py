import requests
import json
import logging

from django.conf import settings

from integrations.constants import (CHECKOUTPG_PAYMENT_CONFIGURATIONS,
                                    CHECKOUTPG_CONFIG_ENDPOINT_V2)

logger = logging.getLogger(__name__)


class CheckoutpgManager(object):

    def __int__(self):
        pass

    def get_configuratoins(self, currency):
        """
        Method for getting configurations
        params: currency
        response: json response from the checkoutpg
        """
        channel_codes = []
        channel_code = CHECKOUTPG_PAYMENT_CONFIGURATIONS.get(
            currency.upper())
        channel_codes.append(channel_code)

        params = {'channel_code': ','.join(channel_codes)}
        headers = {'Api-key': settings.CHECKOUTPG_API_KEY}

        URL = settings.CHECKOUTPG_DOMAIN + CHECKOUTPG_CONFIG_ENDPOINT_V2

        configurations = requests.get(url=URL, params=params, headers=headers)
        if configurations:
            response = json.loads(configurations.text)
            return response
        else:
            logger.error(
                "Unable to fetch config response from checkoutpg for channel:"
                " ".format(channel_code))
            return None

    def get_saved_cards(self):
        """
        Method for getting saved cards
        """
        # https: // checkoutpg - sandbox.yougotagift.com / gateway / checkout
        # / api / v1 / paymenttoken /?
        # key = Cd0ZOH9uzeoeiysbsKWpluzvj3dwP0C_TmC_CZvbfIM &
        # email = christi @ yougotagift.com
        pass
