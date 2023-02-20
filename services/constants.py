TOKEN_TYPE_SAVED_CARD = 'savedcard'
TOKEN_TYPE_CARD = 'card'
TOKEN_TYPE_PAYPAL = 'paypal'
TOKEN_TYPE_APPLEPAY = 'applepay'
RESPONSE_CODE_LIST = [
    '20005',  # Declined - Do not honour
    '20051',  # Insufficient funds
    '20014',  # Invalid card number
    '012',  # Invalid payment
    '029',
    '050',
    '079',
    '084',
    '034',
    '20151',  # Declined - Payment authorization initiated but failed
    None
]
YOUPAY_SESSION_KEY = "youpay-session-id"

APPLEPAY_MERCHANT_IDENTIFIER = "merchant.com.yougotagift.web.test"
APPLEPAY_DOMAIN_NAME = "youpay-frontend-apple-pay.sit.yougotagift.co"
APPLEPAY_DISPLAY_NAME = "YouGotAGift"

APPLEPAY_SUPPORTED_NETWORKS = ["visa", "masterCard", "amex"]
APPLEPAY_MERCHANT_CAPABILITIES = ["supports3DS"]
APPLEPAY_LABEL = "Gift Card"

CLIENT_LOGO_MAX_SIZE = 4194304
CLIENT_LOGO_MAX_HEIGHT = 60
ONE_MB = 1048576
