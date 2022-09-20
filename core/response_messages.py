class YouPayResponse(object):
    SUCCESS = 1000
    UNKNOWN_ERR = 1002
    CHECKOUTPG_CONNECTION_ERROR = 1003

    def __init__(self):
        super(YouPayResponse, self).__init__()
        self.MESSAGE = {}

        service_unavailable = (
            "The service is temporarily unavailable, please try again "
            "later.")

        self.MESSAGE.update({
            self.UNKNOWN_ERR: "Something went wrong",
            self.SUCCESS: "API request completed successfully",
            self.CHECKOUTPG_CONNECTION_ERROR: "Checkoutpg connection error"
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
