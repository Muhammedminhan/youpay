import logging

from core.utils import get_app_config

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TIMEOUT = 10


def get_payment_redirect_url():
    # using low level caching for cache site config,=
    app_config = get_app_config()
    return app_config.front_end_domain if app_config else None
