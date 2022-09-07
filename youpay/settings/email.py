#
# from decouple import config
#
# IS_PRODUCTION = config('IS_PRODUCTION', '')
# IS_SANDBOX = config('IS_SANDBOX', '')
# IS_QA = config('IS_QA', '')
#
# ############################
# # Email Env
# ############################
# EMAIL_HOST = config('EMAIL_HOST', 'smtp.mandrillapp.com')
# EMAIL_HOST_USER = config('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', '')
#
#
# ############################
# # Common Env
# ############################
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# MANDRILL_SENDING_DOMAINS = ['yougotagift.com']
#
# # Email alert settings
#
# if IS_SANDBOX: # Sandbox
#     # The email address that error messages come from
#     SERVER_EMAIL = 'alerts+sandbox@yougotagift.com'
#
#     # Subject-line prefix for error email messages sent
#     # Default:[Django]
#     EMAIL_SUBJECT_PREFIX = '[TabbyPG+Sandbox ] '
#
#     ADMINS = [
#         ('TabbyPG Admin Alerts - Sandbox',
#          'tech-tabbypg-alerts+sandbox@yougotagift.com'),
#     ]
#
#     EMAIL_BACKEND_DEV = (
#         ('Backend Dev - Sandbox',
#          'tech-tabbypg-alerts+sandbox@yougotagift.com'),
#     )
#
#     EMAIL_CUSTOMER_CARE = (
#         ('Customer Care - Sandbox',
#          'tabbypg-alerts+sandbox@yougotagift.com'),
#     )
#
#     EMAIL_ALERTS_FROM = 'YouGotaGift.com Sandbox<%s>' % SERVER_EMAIL
#
#     PAYMENT_RECEIPT_RECEIVERS = (
#         ('Payment Receipt - Sandbox',
#          'tabbypg-alerts+sandbox@yougotagift.com'),
#     )
#
#     EMAIL_HELP = (
#         ('Help - Test', 'tabbypg-alerts+sandbox@yougotagift.com'),
#     )
#
# elif IS_QA:  # Test or QA
#     # The email address that error messages come from
#     SERVER_EMAIL = 'alerts+test@yougotagift.com'
#
#     # Subject-line prefix for error email messages sent
#     # Default:[Django]
#     EMAIL_SUBJECT_PREFIX = '[TabbyPG+Test ] '
#
#     ADMINS = [
#         ('TabbyPG Admin Alerts - Test',
#          'tech-tabbypg-alerts+test@yougotagift.com'),
#     ]
#
#     EMAIL_BACKEND_DEV = (
#         ('Backend Dev - Test',
#          'tech-tabbypg-alerts+test@yougotagift.com'),
#     )
#
#     EMAIL_CUSTOMER_CARE = (
#         ('Customer Care - Test',
#          'tabbypg-alerts+test@yougotagift.com'),
#     )
#
#     EMAIL_ALERTS_FROM = 'YouGotaGift.com Test <%s>' % SERVER_EMAIL
#
#     PAYMENT_RECEIPT_RECEIVERS = (
#         ('Payment Receipt - Test',
#          'tabbypg-alerts+test@yougotagift.com'),
#     )
#
#     EMAIL_HELP = (
#         ('Help - Test', 'tabbypg-alerts+test@yougotagift.com'),
#     )
#
# else:
#     # The email address that error messages come from
#     SERVER_EMAIL = 'alerts@yougotagift.com'
#
#     # Subject-line prefix for error email messages sent
#     # Default:[Django]
#     EMAIL_SUBJECT_PREFIX = '[TabbyPG ] '
#
#     ADMINS = [
#         ('TabbyPG Admin Alerts',
#          'tech-tabbypg-alerts@yougotagift.com'),
#     ]
#
#     EMAIL_BACKEND_DEV = (
#         ('Backend Dev', 'tech-tabbypg-alerts@yougotagift.com'),
#     )
#
#     EMAIL_CUSTOMER_CARE = (
#         ('Customer Care', 'customercare@yougotagift.com'),
#     )
#
#     EMAIL_ALERTS_FROM = 'YouGotaGift.com <%s>' % SERVER_EMAIL
#
#     PAYMENT_RECEIPT_RECEIVERS = (
#         ('Payment Receipt', 'tabbypg-alerts@yougotagift.com'),
#     )
#
#     EMAIL_HELP = (
#         ('Help', 'help@yougotagift.com'),
#     )
