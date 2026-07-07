from django.conf import settings

TOKEN_TYPE_SAVED_CARD = 'savedcard'
TOKEN_TYPE_CARD = 'card'
TOKEN_TYPE_PAYPAL = 'paypal'
TOKEN_TYPE_APPLEPAY = 'applepay'
TOKEN_TYPE_ADCB_POINTS = 'adcb_touchpoints'
TOKEN_TYPE_TABBY_UAE = 'tabby_uae'
TOKEN_TYPE_TABBY_KSA = 'tabby_ksa'
TOKEN_TYPE_TPAY_ETISALAT = 'tpay_etisalat'

PAYMENT_OPTION_NAME_CHOICES = (
    (TOKEN_TYPE_CARD, TOKEN_TYPE_CARD),
    (TOKEN_TYPE_PAYPAL, TOKEN_TYPE_PAYPAL),
    (TOKEN_TYPE_APPLEPAY, TOKEN_TYPE_APPLEPAY),
    (TOKEN_TYPE_SAVED_CARD, TOKEN_TYPE_SAVED_CARD),
    (TOKEN_TYPE_ADCB_POINTS, TOKEN_TYPE_ADCB_POINTS),
    (TOKEN_TYPE_TABBY_UAE, TOKEN_TYPE_TABBY_UAE),
    (TOKEN_TYPE_TABBY_KSA, TOKEN_TYPE_TABBY_KSA),
    (TOKEN_TYPE_TPAY_ETISALAT, TOKEN_TYPE_TPAY_ETISALAT),
)

RESPONSE_CODE_LIST = [
    '20005',  # Declined - Do not honour checkout

    # Insufficient Fund case
    '20051',  # Verify response code from Checkout

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
SOFT_DECLINE_RESPONSE_CODE_STARTSWITH = "20"

YOUPAY_SESSION_KEY = "youpay-session-id"

APPLEPAY_MERCHANT_IDENTIFIER = "merchant.com.yougotagift.web.test"
APPLEPAY_DOMAIN_NAME = "youpay-frontend-apple-pay.sit.yougotagift.co"
APPLEPAY_DISPLAY_NAME = "YouGotAGift"

APPLEPAY_SUPPORTED_NETWORKS = ["visa", "masterCard"]
APPLEPAY_MERCHANT_CAPABILITIES = ["supports3DS"]
APPLEPAY_LABEL = "YOUGotaGift"

CLIENT_LOGO_MAX_SIZE = 4194304
CLIENT_LOGO_MAX_DIMENSION = 60
ONE_MB = 1048576

CURRENCY_UAE = "AED"
CURRENCY_KSA = "SAR"

TABBYPG_STORE_CURRENCIES = [CURRENCY_KSA, ]  # tabbypg active stores
ADCBPG_STORE_CURRENCIES = [CURRENCY_UAE, ]  # adcb active stores
QITAF_STORE_CURRENCIES = [CURRENCY_KSA, ]  # Qitaf active stores
CITI_STORE_CURRENCIES = [CURRENCY_UAE, ]  # Citi active stores
AMAZONPG_STORE_CURRENCIES = [CURRENCY_UAE,
                             CURRENCY_KSA]  # amazonpg active stores

CHECKOUTPG_RESPONSE_MESSAGE_NULL_CODE = 2404

BALANCE_CALCULATION_FAILED_CODE = 1501

TPAY_PUBLIC_KEY = settings.TPAY_PUBLIC_KEY
TPAY_PRIVATE_KEY = settings.TPAY_PRIVATE_KEY
TPAY_MERCHANT_TEMPLATE_KEY = "YOUPay3"
ETISALAT_OPERATOR_CODE = "42402"
TPAY_PRODUCT_CATALOG_NAME = "YouGotaGift"
TPAY_SUCCESS_CODES = [
    "0",
    "100",
    "PaymentCompletedSuccessfully",
    "SucceededAndFailedToContactMerchant"
]
PAYMENT_STATUS_INITIALIZED = 'initialized'
TPAY_STATUS_LABELS = {
    "0": "Success",
    "1": "PIN Send Failed",
    "2": "User Cancelled",
    "3": "MNO Connection Failed",
    "4": "Insufficient Funds",
    "5": "Limit Exceeded",
    "6": "Rejected by Operator",
    "7": "Cancelled by TPay",
    "8": "Inactive Line / Blacklisted User",
    "9": "Unspecified Error",
    "10": "Verification Code Sent",
    "11": "Invalid PIN",
    "13": "Subscriber Does Not Exist",
    "14": "Corporate Line Not Eligible",
    "15": "MNO Charging Error",
    "16": "PIN Expired",
    "18": "Unsupported Price Point",
    "19": "Transaction Timeout",
    "20": "Invalid Password",
    "21": "Transaction Pending",
    "51": "Invalid Digest (Security Error)",
}
COUNTRY_CODE_UAE = 'AE'
TPAY_GATEWAY_CODE = 'TPAY'
