from decouple import config


NETWORK_IDENTITY_URL_SANDBOX = (
    "https://api-gateway.sandbox.ngenius-payments.com/identity/auth/access-token"
)
NETWORK_IDENTITY_URL_PROD = (
    "https://api-gateway.ngenius-payments.com/identity/auth/access-token"
)
NETWORK_API_BASE_URL_SANDBOX = (
    "https://api-gateway.sandbox.ngenius-payments.com"
)
NETWORK_API_BASE_URL_PROD = "https://api-gateway.ngenius-payments.com"

# Configuration Keys (to be moved to settings/env)
NETWORK_API_KEY = config("NETWORK_API_KEY", "")
NETWORK_OUTLET_ID = config("NETWORK_OUTLET_ID", "")
NETWORK_TENANT_REALM = config("NETWORK_TENANT_REALM", "ni")
NETWORK_ENVIRONMENT = config("ENVIRONMENT", "sandbox")


def get_base_url():
    if NETWORK_ENVIRONMENT.lower() == "production":
        return NETWORK_API_BASE_URL_PROD
    return NETWORK_API_BASE_URL_SANDBOX


def get_identity_url():
    if NETWORK_ENVIRONMENT.lower() == "production":
        return NETWORK_IDENTITY_URL_PROD
    return NETWORK_IDENTITY_URL_SANDBOX
