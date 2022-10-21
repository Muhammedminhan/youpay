from .base import *
from decouple import config

try:
    from youpay.settings.security import *
except ImportError:
    pass

YGAG_SECRET_KEY = config('YGAG_SECRET_KEY', None)
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ]
}

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = False
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    "https://*.yougotagift.com",
    "https://*.yougotagift.co",
    "https://*yougotagift.com",
    "https://*yougotagift.co",
]
CORS_ORIGIN_ALLOW_ALL = True
