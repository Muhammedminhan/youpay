import json
import logging
import requests

from core.utils import get_payment_gateway_config
from integrations.constants import (
    CITI_REWARDS_CACHE_KEY, CITI_REWARDS_HUB_CODE
)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class CitiRewardsManager(PaymentHandlers, PaymentRequestView):
    """
    Class to manage citi rewards related operations
    """

    def __init__(self):
        self.citi_reward_config = get_payment_gateway_config(
            CITI_REWARDS_CACHE_KEY, CITI_REWARDS_HUB_CODE)

    def get_payment_header(self):
        """
        Returns headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.citi_reward_config.api_key,
            'X-API-KEY': self.citi_reward_config.api_key
        }
        return headers

    def get_point_balance(self, data):
        """
        calls citi rewards point balance api and returns the balance
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to citi reward point balance "
                "api is {}".format(request_data))
            return request_data, self.SUCCESS
        except Exception as e:
            error = "Error in citi rewards point balance api: {}".format(e)
            logger.error("Exception in citi rewards point balance api:"
                         " {}".format(e))
            return {"error": error}, self.CITI_REWARDS_CONNECTION_ERROR

    def point_redemption(self, data):
        """
        calls citi rewards point redemption api
        """
        try:
            request_data = data['request_data']
            logger.info(
                "Youpay sending request data to citi reward point redemption "
                "api is {}".format(request_data))
            return request_data, self.SUCCESS
        except Exception as e:
            error = "Error in citi rewards point redemption api: {}".format(e)
            logger.error("Exception in citi rewards redemption api:"
                         " {}".format(e))
            return {"error": error}, self.CITI_REWARDS_CONNECTION_ERROR
