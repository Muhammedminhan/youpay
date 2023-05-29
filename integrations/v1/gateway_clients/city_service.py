import json
import logging
import requests

from core.utils import get_payment_gateway_config
from integrations.constants import (
    CITY_REWARDS_CACHE_KEY, CITY_REWARDS_HUB_CODE
)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class CityRewardsManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage city rewards related operations
    """

    def __init__(self):
        self.city_reward_config = get_payment_gateway_config(
            CITY_REWARDS_CACHE_KEY, CITY_REWARDS_HUB_CODE)

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.city_reward_config.api_key,
            'X-API-KEY': self.city_reward_config.api_key
        }
        return headers

    def get_point_balance(self, data):
        """
        calls city rewards point balance api and returns the balance
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to city reward point balance "
                "api is {}".format(request_data))
            return request_data, self.SUCCESS
        except Exception as e:
            error = "Error in city rewards point balance api: {}".format(e)
            logger.error("Exception in city rewards point balance api:"
                         " {}".format(e))
            return {"error": error}, self.CITY_REWARDS_CONNECTION_ERROR

    def point_redemption(self, data):
        """
        calls city rewards point redemption api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to city reward point redemption "
                "api is {}".format(request_data))
            return request_data, self.SUCCESS
        except Exception as e:
            error = "Error in city rewards point redemption api: {}".format(e)
            logger.error("Exception in city rewards redemption api:"
                         " {}".format(e))
            return {"error": error}, self.CITY_REWARDS_CONNECTION_ERROR
