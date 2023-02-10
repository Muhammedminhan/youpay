import logging

from django import forms
from django.core.files.images import get_image_dimensions

from core.utils import get_app_config
from services.constants import (CLIENT_LOGO_MAX_SIZE, CLIENT_LOGO_MAX_HEIGHT,
                                ONE_MB)

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TIMEOUT = 10


def get_payment_redirect_url():
    # using low level caching for cache site config,=
    app_config = get_app_config()
    return app_config.front_end_domain if app_config else None


def api_client_logo_validate(image_file):
    if not image_file:
        raise forms.ValidationError("Logo is required.")
    else:
        if image_file.size > CLIENT_LOGO_MAX_SIZE:
            size_mb = CLIENT_LOGO_MAX_SIZE / ONE_MB
            raise forms.ValidationError(
                "Choose a logo with size below {} MB".format(size_mb))
        width, height = get_image_dimensions(image_file)
        if height > CLIENT_LOGO_MAX_HEIGHT:
            raise forms.ValidationError(
                "The image is {} pixel high. It's supposed to be "
                "{} px max".format(height, CLIENT_LOGO_MAX_HEIGHT))
    return image_file
