from core.messages import GATEWAY_ERROR_OCCURRED
from integrations.constants import APPLEPAY_SUCCESS_CODE_LISTS


class YouPayResponse(object):
    """
    try use error codes as 4-digit numbers, after this onwards, also keep
    ascending order

    1XXX - for general errors
    2XXX - for checkoutpg
    3XXX - for tabbypg
    4XXX - for Amazon Pay
    5XXX - for Apple Pay
    6XXX - for neqaty
    7xxx - for mokafaa
    8xxx - for citi rewards
    9XXX - for qitaf
    10XXX - for AnB
    11XXX - for b2c
    12xxx - for happy credits
    """

    """Youpay related begins"""

    SUCCESS = 1000
    UNKNOWN_ERR = 1002
    PAYMENT_SUCCESS = 1003
    PAYMENT_FAILED = 1004
    CLIENT_TRANSACTION_VERIFICATION_FAILED = 1005
    DUPLICATE_PAYMENT_VERIFICATION = 1006
    BRAND_DETAILS_MISSING = 1007
    MISSING_CLIENT_INFO = 1008
    VALIDATION_FAILED = 1009
    MIDDLEWARE_REDIRECTED = 1307
    TRANSACTION_NOT_FOUND = 1404
    MAX_PAYMENT_ATTEMPT_REACHED = 1416
    BALANCE_CALCULATION_FAILED = 1501

    TRANSACTION_ALREADY_CLOSED = 1600
    REQUIRED_DATA_MISSING = 1601
    DATA_CORRUPTED = 1602
    OTP_ERROR = 1010
    OTP_EXPIRED = 1017
    INSUFFICIENT_BALANCE = 1018
    OTP_STILL_VALID = 1019

    """Youpay related ends"""

    """checkoutpg related begins"""
    CHECKOUTPG_CONNECTION_ERROR = 2003
    CHECKOUTPG_RESPONSE_FAILED = 2400
    CHECKOUTPG_RESPONSE_MESSAGE_NULL = 2404
    PRE_AUTH = 2405
    """checkoutpg related ends"""

    """tabbypg related begins"""
    TABBYPG_CONNECTION_ERROR = 3006
    TABBYPG_VERIFICATION_FAILED = 3600
    TABBYPG_VERIFICATION_SUCCESS = 3601
    TABBYPG_VERIFICATION_ERROR = 3603
    TABBYPG_VERIFICATION_EXCEPTION = 3604
    TABBYPG_DUPLICATE_VERIFICATION = 3605
    TABBYPG_PAYMENT_REJECTED = 3606

    """tabbypg related ends"""

    """b2cpayback related begins"""
    B2CPAYBACK_VERIFICATION_FAILED = 11600
    B2CPAYBACK_VERIFICATION_SUCCESS = 11601
    B2CPAYBACK_VERIFICATION_FAILED_TO_PROCESS = 11603
    B2CPAYBACK_VERIFICATION_EXCEPTION = 11604

    """b2cpayback related ends"""

    """Amazonpay related begins"""
    AMAZONPG_CONNECTION_ERROR = 4002
    AMAZONPG_CONNECTION_RETRY = 4003
    """Amazonpay related ends"""

    """happy credits related begins"""
    HAPPY_CREDITS_CONNECTION_ERROR = 12002
    HAPPY_CREDITS_VERIFICATION_FAILED = 12600
    HAPPY_REDEMPTION_SUCCESS = 12601
    HAPPY_VERIFICATION_EXCEPTION = 12604
    HAPPY_CREDITS_INSUFFICIENT_FUND = 12701

    """happy credits related ends"""

    """Apple Pay back related begins"""
    APPLE_PAY_CONNECTION_ERROR = 5000

    # Begin: status update codes with Apple Pay
    APPLE_PAY_STATUS_UPDATED_PENDING = 5101
    APPLE_PAY_STATUS_UPDATED_AUTHORIZED = 5102
    APPLE_PAY_STATUS_UPDATED_PAID = 5103
    # End: status update codes with Apple Pay

    APPLE_PAY_BAD_REQUEST = 5400
    APPLE_PAY_SUCCESS = 5200
    APPLE_PAY_CREATED = 5201
    APPLE_PAY_REDIRECT = 5308

    # This is to provide success http status codes in API response
    APPLEPAY_SUCCESS_CODES = APPLEPAY_SUCCESS_CODE_LISTS
    """Apple Pay back related ends"""

    """Neqaty related begins"""
    NEQATY_CONNECTION_ERROR = 6002
    NEQATY_PHONE_NUMBER_SAVE_FAILED = 6003
    NEQATY_PHONE_NUMBER_SAVED = 6004
    NEQATY_PHONE_NUMBER_FAILED_TO_FETCH = 6005
    NEQATY_VERIFICATION_FAILED_TO_PROCESS = 6006
    NEQATY_VERIFICATION_FAILED = 6007
    NEQATY_VERIFICATION_EXCEPTION = 6008
    NEQATY_BALANCE_CALCULATION_FAILED = 6009
    NEQATY_NOT_ENABLED = 6401
    NEQATY_ALREADY_COLLECTED = 6402
    NEQATY_REWARD_POINT_MIN_AMT_NOT_MET = 6403
    NEQATY_NOT_SUPPORTED = 6404

    """Qitaf related ends"""

    """Citi rewards related begins"""
    CITI_REWARDS_CONNECTION_ERROR = 8002
    CITI_REWARDS_INSUFFICIENT_BALANCE = 8003
    CITI_REWARDS_OTP_EXPIRED_OR_ATTEMPTS_EXCEEDED = 8004
    CITI_REWARDS_ALREADY_REDEEMED = 8005
    CITI_REWARDS_VALIDATION_ERROR = 8006
    CITI_REWARDS_INVALID_CUSTOMER = 8007
    CITI_REWARDS_INVALID_OTP = 8008
    CITI_REWARDS_USER_BLOCKED = 8009
    """Citi rewards related ends"""

    """Qitaf related begins"""
    QITAF_CONNECTION_ERROR = 9002
    QITAF_PHONE_NUMBER_SAVE_FAILED = 9003
    QITAF_PHONE_NUMBER_SAVED = 9004
    QITAF_PHONE_NUMBER_FAILED_TO_FETCH = 9005
    QITAF_VERIFICATION_FAILED_TO_PROCESS = 9006
    QITAF_VERIFICATION_FAILED = 9007
    QITAF_VERIFICATION_EXCEPTION = 9008
    QITAF_BALANCE_CALCULATION_FAILED = 9009
    QITAF_NOT_ENABLED = 9401
    QITAF_ALREADY_COLLECTED = 9402
    QITAF_REWARD_POINT_MIN_AMT_NOT_MET = 9403
    QITAF_NOT_SUPPORTED = 9404

    """Qitaf related ends"""

    """Mokafaa related begins"""
    MOKAFA_CONNECTION_ERROR = 7002
    MOKAFA_PHONE_NUMBER_SAVE_FAILED = 7003
    MOKAFA_PHONE_NUMBER_SAVED = 7004
    MOKAFA_PHONE_NUMBER_FAILED_TO_FETCH = 7005
    MOKAFA_ALREADY_COLLECTED = 7402
    MOKAFA_NOT_SUPPORTED = 7404
    MOKAFAA_VERIFICATION_FAILED = 7007
    MOKAFAA_VERIFICATION_EXCEPTION = 7008
    MOKAFAA_PAYMENT_FAILED = 7009
    MOKAFAA_OTP_STILL_VALID = 7010

    """Mokafa related ends """

    """AnB related begins"""
    ANB_CONNECTION_ERROR = 10002
    ANB_VALIDATION_FAILED = 10003
    ANB_MEMBER_BALANCE_INSUFFICIENT = 10604
    ANB_DUPLICATE_MOBILE_NUMBER = 10607
    ANB_USER_DOES_NOT_EXIST = 10609
    ANB_OTP_STILL_VALID = 10610
    ANB_INVALID_OTP = 10704
    ANB_INVALID_OTP_RESENT = 10706
    ANB_OTP_EXPIRED = 10708
    ANB_PAYMENT_FAILED = 10709
    ANB_VERIFICATION_FAILED = 10807
    ANB_VERIFICATION_EXCEPTION = 10808
    """AnB related ends """

    """PayPal related begins"""
    PAYPAL_CONNECTION_ERROR = 18001
    PAYPAL_VERIFICATION_FAILED = 18002
    PAYPAL_VERIFICATION_SUCCESS = 18003
    PAYPAL_VERIFICATION_EXCEPTION = 18004
    PAYPAL_PAYMENT_FAILED = 18005
    PAYPAL_INSUFFICIENT_FUNDS = 18006
    PAYPAL_INVALID_REQUEST = 18007
    PAYPAL_NOT_SUPPORTED = 18008
    PAYAPL_PAYMENT_INCOMPLETE = 18009
    """PayPal related ends"""

    MESSAGE = {}

    def __init__(self):
        super(YouPayResponse, self).__init__()

        self.MESSAGE.update({
            self.VALIDATION_FAILED: "Data validation failed",
            self.UNKNOWN_ERR: "Something went wrong",
            self.DATA_CORRUPTED: "Data corrupted",
            self.SUCCESS: "API request completed successfully",
            self.PAYMENT_SUCCESS: "Transaction success",
            self.PAYMENT_FAILED: "Payment failed",
            self.BRAND_DETAILS_MISSING: "Brand details missing",
            self.OTP_ERROR: "Invalid OTP",
            self.OTP_EXPIRED: "OTP is expired",
            self.INSUFFICIENT_BALANCE: (
                "This member balance is insufficient for redemptions"),
            self.BALANCE_CALCULATION_FAILED:
                "Failed to calculate the point program balance. Please try "
                "again with another payment option.",

            self.CHECKOUTPG_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.CHECKOUTPG_RESPONSE_FAILED: GATEWAY_ERROR_OCCURRED,
            self.DUPLICATE_PAYMENT_VERIFICATION: (
                "Duplicate payment verification"),

            self.APPLE_PAY_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.APPLE_PAY_BAD_REQUEST: "Applepay bad request",
            self.APPLE_PAY_SUCCESS: "Applepay request success",
            self.APPLE_PAY_CREATED: "Applepay request created",
            self.APPLE_PAY_STATUS_UPDATED_PENDING: "Apple pay payment "
                                                   "status updated to "
                                                   "pending",
            self.APPLE_PAY_STATUS_UPDATED_AUTHORIZED: "Apple pay payment "
                                                      "status updated to "
                                                      "authorized",
            self.APPLE_PAY_STATUS_UPDATED_PAID: "Apple pay payment status "
                                                "updated to paid",
            self.APPLE_PAY_REDIRECT: "Apple pay redirect",
            self.TABBYPG_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.TABBYPG_VERIFICATION_FAILED: "Tabbypg verification failed",
            self.TABBYPG_PAYMENT_REJECTED: (
                "Your Tabby payment has been rejected"),
            self.AMAZONPG_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.AMAZONPG_CONNECTION_RETRY: "Amazonpg retry to check webhook",
            self.HAPPY_CREDITS_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.HAPPY_CREDITS_INSUFFICIENT_FUND: "Insufficient balance",
            self.HAPPY_VERIFICATION_EXCEPTION: "Exception on Verification",

            self.QITAF_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.QITAF_PHONE_NUMBER_SAVE_FAILED: (
                "Qitaf Phone number failed to save"),
            self.QITAF_PHONE_NUMBER_SAVED: (
                "Qitaf Phone number updated"),
            self.QITAF_PHONE_NUMBER_FAILED_TO_FETCH: (
                "Qitaf Phone number failed to fetch"),
            self.QITAF_VERIFICATION_FAILED_TO_PROCESS: "Verification failed to process",
            self.QITAF_VERIFICATION_FAILED: "Verification failed",
            self.QITAF_VERIFICATION_EXCEPTION: "Verification failed.",
            self.QITAF_NOT_SUPPORTED: "Qitaf Forbidden, or partial redemption not supported.",
            self.QITAF_ALREADY_COLLECTED: "Qitaf Reward collected Already.",
            self.QITAF_BALANCE_CALCULATION_FAILED: "Qitaf Balance calculation failed.",

            self.NEQATY_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.NEQATY_PHONE_NUMBER_SAVE_FAILED: (
                "NEQATY Phone number failed to save"),
            self.NEQATY_PHONE_NUMBER_SAVED: (
                "NEQATY Phone number updated"),
            self.NEQATY_PHONE_NUMBER_FAILED_TO_FETCH: (
                "NEQATY Phone number failed to fetch"),
            self.NEQATY_VERIFICATION_FAILED_TO_PROCESS: "Verification failed to process",
            self.NEQATY_VERIFICATION_FAILED: "Verification failed",
            self.NEQATY_VERIFICATION_EXCEPTION: "Exception on Verification",
            self.NEQATY_NOT_SUPPORTED: "NEQATY Forbidden, or partial redemption not supported.",
            self.NEQATY_ALREADY_COLLECTED: "NEQATY Reward collected Already.",
            self.NEQATY_BALANCE_CALCULATION_FAILED: "NEQATY Balance calculation failed.",

            self.MOKAFA_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.MOKAFA_PHONE_NUMBER_SAVE_FAILED: (
                "MOKAFA Phone/cic number failed to save"),
            self.MOKAFA_PHONE_NUMBER_SAVED: (
                "MOKAFA Phone/cic number updated"),
            self.MOKAFA_PHONE_NUMBER_FAILED_TO_FETCH: (
                "MOKAFA Phone/cic number failed to fetch"),
            self.MOKAFA_ALREADY_COLLECTED: "MOKAFA Reward collected Already.",
            self.MOKAFA_NOT_SUPPORTED: (
                "Mokafaa Forbidden, or partial redemption not supported."),
            self.MOKAFAA_VERIFICATION_FAILED: "Verification failed",
            self.MOKAFAA_VERIFICATION_EXCEPTION: "Verification failed.",
            self.MOKAFAA_OTP_STILL_VALID: "Last generated OTP is still valid",

            self.CLIENT_TRANSACTION_VERIFICATION_FAILED: (
                "Transaction verification failed"),
            self.TRANSACTION_NOT_FOUND: "Transaction not found",
            self.MISSING_CLIENT_INFO: "API Client data missing",
            self.MAX_PAYMENT_ATTEMPT_REACHED: "Max payment attempt reached",
            self.MIDDLEWARE_REDIRECTED: "Request redirected",

            self.B2CPAYBACK_VERIFICATION_SUCCESS: "Payment verified",
            self.B2CPAYBACK_VERIFICATION_FAILED_TO_PROCESS: "verification "
                                                            "failed",
            self.B2CPAYBACK_VERIFICATION_EXCEPTION: "Exception occurred ",
            self.B2CPAYBACK_VERIFICATION_FAILED: "Response failed during b2c"
                                                 " verification",
            self.PRE_AUTH: "Authentication not approved"
                           " verification",

            self.CITI_REWARDS_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.CITI_REWARDS_INSUFFICIENT_BALANCE: (
                "You don't have enough points to make this transaction"),
            self.CITI_REWARDS_OTP_EXPIRED_OR_ATTEMPTS_EXCEEDED: (
                "Exceeded the limit. Please try again later"),
            self.CITI_REWARDS_ALREADY_REDEEMED: (
                "Transaction is already redeemed."),
            self.CITI_REWARDS_VALIDATION_ERROR: (
                "Missing or invalid Parameters"),
            self.CITI_REWARDS_INVALID_CUSTOMER: (
                "Invalid details, please try again"
            ),
            self.CITI_REWARDS_INVALID_OTP: "Invalid/Expired OTP",
            self.CITI_REWARDS_USER_BLOCKED: (
                "Exceeded the limit. Please try again later"
            ),
            self.TRANSACTION_ALREADY_CLOSED: "Transaction already processed!",

            self.ANB_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.ANB_VALIDATION_FAILED: "Validation failed",
            self.ANB_MEMBER_BALANCE_INSUFFICIENT: "This member balance is "
                                                  "insufficient for "
                                                  "redemptions",
            self.ANB_DUPLICATE_MOBILE_NUMBER: "Duplicate mobile number, "
                                              "please try searching for the "
                                              "customer using loyalty card "
                                              "number or CIF",
            self.ANB_USER_DOES_NOT_EXIST: "User does not exist",
            self.ANB_OTP_STILL_VALID: "Last generated OTP is still valid",
            self.ANB_INVALID_OTP: "OTP is invalid",
            self.ANB_INVALID_OTP_RESENT: "Invalid OTP. OTP was resent, "
                                         "please check it again",
            self.ANB_OTP_EXPIRED: "OTP has expired",
            self.ANB_PAYMENT_FAILED: "Payment failed",
            self.ANB_VERIFICATION_FAILED: "Verification failed",
            self.ANB_VERIFICATION_EXCEPTION: "Verification failed",

            self.PAYPAL_CONNECTION_ERROR: GATEWAY_ERROR_OCCURRED,
            self.PAYPAL_VERIFICATION_FAILED: "PayPal verification failed",
            self.PAYPAL_VERIFICATION_EXCEPTION: "PayPal verification exception",
            self.PAYPAL_PAYMENT_FAILED: "PayPal payment failed",
            self.PAYPAL_INSUFFICIENT_FUNDS: "PayPal insufficient funds",
            self.PAYPAL_INVALID_REQUEST: "PayPal invalid request",
            self.PAYPAL_NOT_SUPPORTED: "PayPal not supported",
            self.PAYAPL_PAYMENT_INCOMPLETE: "PayPal payment incomplete",
        })

    def get_400_message(self, message):
        return {'errors': {'code': 400, 'message': message}}

    def get_403_message(self, message):
        return {'errors': {'code': 403, 'message': message}}

    def get_404_message(self, message):
        return {'errors': {'code': 404, 'message': message}}

    def get_error_dict(self, error_code, serializer_error=None):
        error_dict = {}
        error_string = ""

        if serializer_error:
            for k, v in serializer_error.items():
                error_string = error_string + k + " : " + v[0] + "\n"
            error_dict['message'] = error_string
            error_dict['code'] = error_code
            return {'errors': error_dict}

        if error_code:
            message = self.MESSAGE.get(error_code)
            if not isinstance(message, dict):
                message = self.MESSAGE.get(error_code)
            error_dict['message'] = message
            error_dict['code'] = error_code
            return {'errors': error_dict}
        else:
            message = self.MESSAGE.get(self.UNKNOWN_ERR)
            if not isinstance(message, dict):
                message = self.MESSAGE.get(self.UNKNOWN_ERR)
            error_dict['message'] = message
            error_dict['code'] = self.UNKNOWN_ERR
            return {'errors': error_dict}

    def get_success_dict(self, code, success_dict=None):
        if success_dict is None:
            success_dict = {}
        success_dict['message'] = self.MESSAGE.get(code)
        success_dict['code'] = code
        return success_dict
