from django.conf import settings

TPAY_PUBLIC_KEY = settings.TPAY_PUBLIC_KEY
TPAY_PRIVATE_KEY = settings.TPAY_PRIVATE_KEY
TPAY_MERCHANT_TEMPLATE_KEY = "YOUPay3"
ETISALAT_OPERATOR_CODE = "42402"
TPAY_PRODUCT_CATALOG_NAME = "YouGotaGift"
TPAY_SUCCESS_CODES = [
    "0",
    "100",
    "Success",
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
