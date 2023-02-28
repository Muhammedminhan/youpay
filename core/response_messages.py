class YouPayResponse(object):
    """
    try use error codes as 4-digit numbers, after this onwards, also keep
    ascending order

    1XXX - for general errors
    2XXX - for checkoutpg
    3XXX - for tabbypg
    4XXX - for Amazon Pay
    5XXX - for b2c
    6XXX - for youpay
    7xxx - for happy credits
    """

    SUCCESS = 1000
    UNKNOWN_ERR = 1002

    PAYMENT_FAILED = 1004
    CLIENT_TRANSACTION_VERIFICATION_FAILED = 1005
    TRANSACTION_NOT_FOUND = 1404

    """checkoutpg related begins"""
    CHECKOUTPG_CONNECTION_ERROR = 2003
    """checkoutpg related ends"""

    """tabbypg related begins"""
    TABBYPG_CONNECTION_ERROR = 1006
    """tabbypg related ends"""

    """b2cpayback related begins"""
    TRANSACTION_NOT_FOUND = 6404
    """b2cpayback related ends"""

    """Amazonpay related begins"""
    AMAZONPG_CONNECTION_ERROR = 4002
    """Amazonpay related ends"""

    """happy credits related begins"""
    HAPPY_CREDITS_CONNECTION_ERROR = 7002
    """happy credits related ends"""

    """Youpay related begins"""
    MISSING_CLIENT_INFO = 6000
    """Youpay related ends"""

    MESSAGE = {}

    def __init__(self):
        super(YouPayResponse, self).__init__()
        service_unavailable = (
            "The service is temporarily unavailable, please try again "
            "later.")

        self.MESSAGE.update({
            self.UNKNOWN_ERR: "Something went wrong",
            self.SUCCESS: "API request completed successfully",
            self.CHECKOUTPG_CONNECTION_ERROR: "Checkoutpg connection error",
            self.PAYMENT_FAILED: "Payment failed",
            self.TABBYPG_CONNECTION_ERROR: "Tabbypg connection error",
            self.AMAZONPG_CONNECTION_ERROR: "Amzonpg connection error",
            self.HAPPY_CREDITS_CONNECTION_ERROR: (
                "Happy credits connection error"),
            self.CLIENT_TRANSACTION_VERIFICATION_FAILED: (
                "Transaction verification failed"),
            self.TRANSACTION_NOT_FOUND: "Transaction not found",
            self.MISSING_CLIENT_INFO: "API Client data missing"
        })

    def get_400_message(self, message):
        return {'errors': {'code': 400, 'message': message}}

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
