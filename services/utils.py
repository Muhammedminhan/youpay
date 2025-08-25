import logging

from core.utils import get_app_config
from integrations.constants import CHECKOUTPG_CHANNEL_CONFIGURATIONS

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TIMEOUT = 10


def get_payment_redirect_url():
    # using low level caching for cache site config,=
    app_config = get_app_config()
    return app_config.front_end_domain if app_config else None


def get_client_channel_code(client, transaction=None):
    channel_code = None
    if transaction:
        currency = transaction.currency
        platform = transaction.platform
        checkout_channel_code = transaction.api_client.checkout_channel_code
        if checkout_channel_code:
            channelcode = checkout_channel_code
        else:
            channelcode = CHECKOUTPG_CHANNEL_CONFIGURATIONS
        channel_code = channelcode.get(currency, {}).get(platform.upper())
    else:
        checkout_channel_code = client.checkout_channel_code
        if checkout_channel_code:
            channelcode = checkout_channel_code
        else:
            channelcode = CHECKOUTPG_CHANNEL_CONFIGURATIONS
        for channels in channelcode.values():
            channel_code = next(iter(channels.values()), None)
    return channel_code
