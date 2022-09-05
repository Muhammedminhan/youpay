# local development settings
from .base import *

import os
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))))
SITE_DOMAIN = config('SITE_DOMAIN', '')

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}

# Celery settings
CELERY_BROKER_URL = 'redis://localhost:6379/2'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/4'

# Redis settings
REDIS_HOST = 'localhost'

# Static Settings ( static url, static root et)
MEDIA_URL = "http://%s/%s/" % (SITE_DOMAIN, 'media')

STATIC_URL = "http://%s/%s/" % (SITE_DOMAIN, 'static')

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'app_static')]

# MailCatcher Settings
EMAIL_PORT = 1025

EMAIL_USE_TLS = False

