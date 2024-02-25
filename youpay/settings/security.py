
# Security settings
# Sandbox, production environments use these settings, so excluding it for
# development environment.
SITE_SECURE = True
# Whether or not to construct URLs as https or http
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
# SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SAMESITE = 'lax'
# TOKEN_COOKIE_DOMAIN = '.yougotagift.co'
