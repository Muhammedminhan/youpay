from decouple import config

FLAGGED_PAYMENT_MAIL = "Flagged Mail Alert"
environment = config('ENVIRONMENT', '')

EMAIL_TYPES = {
    (FLAGGED_PAYMENT_MAIL, FLAGGED_PAYMENT_MAIL)
}

HUB_LINK = config('HUB_LINK', '')
AMAZON_HUB_LINK = config('AMAZON_HUB_LINK', '')
