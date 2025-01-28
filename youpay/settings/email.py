from decouple import config

IS_PRODUCTION = config('IS_PRODUCTION', '')
IS_SANDBOX = config('IS_SANDBOX', '')
IS_QA = config('IS_QA', '')
environment = config('ENVIRONMENT', '')

############################
# Email Env
############################
EMAIL_HOST = config('EMAIL_HOST', 'smtp.mandrillapp.com')
EMAIL_HOST_USER = config('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', '')

############################
# Common Env
############################
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
MANDRILL_SENDING_DOMAINS = ['yougotagift.com']

############################
# MailEngine Env
############################
MAIL_ENGINE_API_KEY = config('MAIL_ENGINE_API_KEY', '')
MAIL_ENGINE_API_SECRET = config('MAIL_ENGINE_API_SECRET', '')

# Email alert settings

if environment == 'production':
    # The email address that error messages come from
    SERVER_EMAIL = 'alerts@yougotagift.com'

    # Subject-line prefix for error email messages sent
    # Default:[Django]
    EMAIL_SUBJECT_PREFIX = '[Youpay ] '

    ADMINS = [
        ('Youpay Admin Alerts',
         'tech-youpay-alerts@yougotagift.com'),
    ]

    EMAIL_BACKEND_DEV = (
        ('Backend Dev', 'tech-youpay-alerts@yougotagift.com'),
    )

    EMAIL_CUSTOMER_CARE = (
        ('Customer Care', 'customercare@yougotagift.com'),
    )

    EMAIL_ALERTS_FROM = 'YouGotaGift.com <%s>' % SERVER_EMAIL

    PAYMENT_RECEIPT_RECEIVERS = (
        ('Payment Receipt', 'youpay-alerts@yougotagift.com'),
    )

    EMAIL_HELP = (
        ('Help', 'customercare@yougotagift.com'),
    )

elif environment == 'sandbox':  # Sandbox
    # The email address that error messages come from
    SERVER_EMAIL = 'alerts+sandbox@yougotagift.com'

    # Subject-line prefix for error email messages sent
    # Default:[Django]
    EMAIL_SUBJECT_PREFIX = '[Youpay+Sandbox ] '

    ADMINS = [
        ('Youpay Admin Alerts - Sandbox',
         'tech-youpay-alerts+sandbox@yougotagift.com'),
    ]

    EMAIL_BACKEND_DEV = (
        ('Backend Dev - Sandbox',
         'tech-youpay-alerts+sandbox@yougotagift.com'),
    )

    EMAIL_CUSTOMER_CARE = (
        ('Customer Care - Sandbox',
         'youpay-alerts+sandbox@yougotagift.com'),
    )

    EMAIL_ALERTS_FROM = 'YouGotaGift.com Sandbox<%s>' % SERVER_EMAIL

    PAYMENT_RECEIPT_RECEIVERS = (
        ('Payment Receipt - Sandbox',
         'youpay-alerts+sandbox@yougotagift.com'),
    )

    EMAIL_HELP = (
        ('Help - Test', 'youpay-alerts+sandbox@yougotagift.com'),
    )

elif environment == 'qa':  # Test or QA
    # The email address that error messages come from
    SERVER_EMAIL = 'alerts+test@yougotagift.com'

    # Subject-line prefix for error email messages sent
    # Default:[Django]
    EMAIL_SUBJECT_PREFIX = '[Youpay+Test ] '

    ADMINS = [
        ('Youpay Admin Alerts - Test',
         'tech-youpay-alerts+test@yougotagift.com'),
    ]

    EMAIL_BACKEND_DEV = (
        ('Backend Dev - Test',
         'tech-youpay-alerts+test@yougotagift.com'),
    )

    EMAIL_CUSTOMER_CARE = (
        ('Customer Care - Test',
         'youpay-alerts+test@yougotagift.com'),
    )

    EMAIL_ALERTS_FROM = 'YouGotaGift.com Test <%s>' % SERVER_EMAIL

    PAYMENT_RECEIPT_RECEIVERS = (
        ('Payment Receipt - Test',
         'youpay-alerts+test@yougotagift.com'),
    )

    EMAIL_HELP = (
        ('Help - Test', 'tabbypg-alerts+test@yougotagift.com'),
    )
