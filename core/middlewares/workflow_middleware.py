import json
import logging

from django.http import JsonResponse

from core.constants import (
    MAX_PAYMENT_RETRY_COUNT,
    CHECK_PAYMENT_STATUS_CLASSES,
    VERIFY_PAYMENT_CLASSES)
from core.exceptions import (
    TransactionNotFound,
    TransactionAlreadyPaid,
    TransactionAlreadyCancelled, TransactionAlreadyExpired,
    TransactionAlreadyVerified, TransactionMaxAttemptReached,
    TransactionAlreadyProcessed)
from core.messages import (
    COMMON_ERROR_MESSAGE_EN, MIDDLEWARE_STATUS_CHECK_MESSAGE,
    MIDDLEWARE_ALREADY_PAID_MESSAGE)
from core.response_messages import YouPayResponse
from payments.constants import (
    PAYMENT_STATUS_CANCELLED, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_METHOD_APPLEPAY,
    PAYMENT_STATUS_EXPIRED, SUCCESS_REDIRECT_STATUS_LIST,
    RETRY_END_STATUS_LIST)

logger = logging.getLogger(__name__)


class PaymentStatusCheckMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.response = {}

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):

        view_name = request.resolver_match.view_name
        if view_name in CHECK_PAYMENT_STATUS_CLASSES:
            '''
            checks for
            1. transaction exist or not
            2. already paid or not
            3. already cancelled or not
            4. already expired or not
            5. already reached max attempt or not 
            '''
            from core.utils import decrypt_string
            from services.v1.views.common import (YouPayTransactionCRUD)
            youpay_obj = YouPayTransactionCRUD()

            # to import youpay codes
            youpay_message_obj = YouPayResponse()
            log_message = ""
            code = None
            transaction_id = None
            try:
                # this will check for only post requests
                if request.method == 'POST':
                    data = json.loads(request.body)
                    transaction_id = decrypt_string(
                        data.get('transaction_id', None))

                    logger.info(
                        "Middleware : {} Request {} Started for {}".format(
                            request.method, view_name, transaction_id))

                    transaction_obj = youpay_obj.get_youpay_transaction_data(
                        transaction_id)

                    self.check_transaction_obj(transaction_obj,
                                               youpay_message_obj)

                    self.check_transaction_already_paid(transaction_obj,
                                                        youpay_message_obj)

                    self.check_transaction_already_cancelled(
                        transaction_obj,
                        youpay_message_obj)

                    self.check_transaction_expired(transaction_obj,
                                                   youpay_message_obj)

                    self.check_already_attempted(transaction_obj,
                                                 youpay_message_obj)

            except TransactionMaxAttemptReached:
                return JsonResponse(self.response, status=200)

            except TransactionAlreadyExpired:
                return JsonResponse(self.response, status=200)

            except TransactionAlreadyCancelled:
                return JsonResponse(self.response, status=200)

            except TransactionAlreadyPaid:
                return JsonResponse(self.response, status=200)

            except TransactionAlreadyProcessed:
                return JsonResponse(self.response, status=404)

            except TransactionNotFound:
                log_message = "TransactionNotFound"
                code = youpay_message_obj.TRANSACTION_NOT_FOUND
                logger.error(log_message)
                self.common_error_response(COMMON_ERROR_MESSAGE_EN, code)

            except Exception as e:
                log_message = "Exception in middleware: {}".format(e)
                code = youpay_message_obj.UNKNOWN_ERR
                logger.error(log_message)
                self.common_error_response(COMMON_ERROR_MESSAGE_EN, code)

            finally:
                logger.info("Middleware : {} Request {} Ended for {}".format(
                    request.method, view_name, transaction_id))

    def get_payment_response(
            self, redirect_url, transaction_message, youpay_message_obj,
            is_success=True):
        data = {
            "is_redirect": True,
            "is_success": is_success,
            "redirect_url": redirect_url,
            "message": transaction_message,
            "code": youpay_message_obj.MIDDLEWARE_REDIRECTED,
        }
        return data

    def get_redirect_url(self, url, transaction_id):
        redirect_url = ('{}?transaction_id={}'.format(url, transaction_id))
        return redirect_url

    def check_transaction_obj(self, transaction_obj, youpay_message_obj):
        if transaction_obj is None:
            raise TransactionNotFound(
                youpay_message_obj.TRANSACTION_NOT_FOUND)

    def check_transaction_already_paid(self, transaction_obj,
                                       youpay_message_obj):
        transaction_status = transaction_obj.payment_status
        transaction_id = transaction_obj.transaction_id

        if transaction_status == PAYMENT_STATUS_PAID:
            """
            This will redirect already paid transaction to success url
            """
            transaction_message = MIDDLEWARE_ALREADY_PAID_MESSAGE

            logger.info("{} {} ".format(transaction_message, transaction_id))

            redirect_url = self.get_redirect_url(
                transaction_obj.success_url, transaction_id)
            is_success = True

            # Preparing response data as per the payment API response
            self.response = self.get_payment_response(
                redirect_url, transaction_message, youpay_message_obj,
                is_success)
            raise TransactionAlreadyPaid

    def check_transaction_already_cancelled(self, transaction_obj,
                                            youpay_message_obj):
        transaction_status = transaction_obj.payment_status
        transaction_id = transaction_obj.transaction_id

        if transaction_status == PAYMENT_STATUS_CANCELLED:
            """
            This will redirect to cancel url, so wont able to pay for
            already canceled transactions
            """

            transaction_message = MIDDLEWARE_STATUS_CHECK_MESSAGE
            logger.info("{} {} ".format(transaction_message, transaction_id))

            redirect_url = self.get_redirect_url(
                transaction_obj.cancel_url, transaction_id)
            is_success = False

            # Preparing response data as per the payment API response
            self.response = self.get_payment_response(
                redirect_url, transaction_message, youpay_message_obj,
                is_success)
            raise TransactionAlreadyCancelled

    def check_transaction_expired(self, transaction_obj, youpay_message_obj):
        transaction_status = transaction_obj.payment_status
        transaction_id = transaction_obj.transaction_id

        if transaction_status == PAYMENT_STATUS_EXPIRED:
            """
            This will redirect to failure url, so wont able to pay for
            already expired transactions
            """

            transaction_message = MIDDLEWARE_STATUS_CHECK_MESSAGE
            logger.info("{} {} ".format(transaction_message, transaction_id))

            redirect_url = self.get_redirect_url(
                transaction_obj.failure_url, transaction_id)
            is_success = False

            # Preparing response data as per the payment API response
            self.response = self.get_payment_response(
                redirect_url, transaction_message, youpay_message_obj,
                is_success)
            raise TransactionAlreadyExpired

    def check_maximum_retry_attempt(self, transaction_obj,
                                    youpay_message_obj, youpay_obj, data):

        if transaction_obj.retry_count >= MAX_PAYMENT_RETRY_COUNT:
            """
            if retry count is more than MAX_RETRY_COUNT, then
            cancel the transaction and redirect to cancel url
            """

            message = "You have reached your maximum retry attempt"

            youpay_obj.update_youpay_transaction_data(
                {
                    "transaction_id": transaction_obj.transaction_id,
                    "payment_status": PAYMENT_STATUS_CANCELLED
                }
            )

            redirect_url = self.get_redirect_url(
                transaction_obj.cancel_url, transaction_obj.transaction_id)

            # Preparing response data as per the payment API response
            data = {
                "is_redirect": True,
                "is_success": False,
                "redirect_url": redirect_url,
                "message": message,
                "code": youpay_message_obj.MAX_PAYMENT_ATTEMPT_REACHED,
            }
            self.response = data
            raise TransactionMaxAttemptReached

        else:

            # avoid retry count increment for applepay authorize
            # and paid transactions
            payment_stage = data.get('payment_stage', None)

            if not (payment_stage == PAYMENT_STATUS_AUTHORIZED or
                    payment_stage == PAYMENT_STATUS_PAID
                    and transaction_obj.payment_method ==
                    PAYMENT_METHOD_APPLEPAY):
                retry_count = transaction_obj.retry_count + 1

                youpay_obj.update_youpay_transaction_data(
                    {
                        "transaction_id": transaction_obj.transaction_id,
                        "retry_count": retry_count
                    }
                )

    def check_already_attempted(self, transaction_obj, youpay_message_obj):
        transaction_status = transaction_obj.payment_status
        transaction_id = transaction_obj.transaction_id

        if transaction_status in RETRY_END_STATUS_LIST:
            """
            request will redirect to not found page.
            """

            transaction_message = MIDDLEWARE_STATUS_CHECK_MESSAGE
            logger.info("{} {} ".format(
                transaction_message, transaction_id))

            redirect_url = self.get_redirect_url(
                transaction_obj.failure_url, transaction_id)
            is_success = False

            self.response = self.get_payment_response(
                redirect_url, transaction_message, youpay_message_obj,
                is_success)
            raise TransactionAlreadyProcessed


    def common_error_response(self, message, code):
        return JsonResponse(
            {
                'errors': {
                    'message': message,
                    'code': code
                }
            },
            status=400)


class PaymentVerificationCheckMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.response = {}

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        view_name = request.resolver_match.view_name
        if view_name in VERIFY_PAYMENT_CLASSES:
            from core.utils import decrypt_string
            from services.v1.views.common import (YouPayTransactionCRUD)

            youpay_obj = YouPayTransactionCRUD()
            youpay_message_obj = YouPayResponse()

            transaction_id = decrypt_string(request.GET.get('id'))

            logger.info("Middleware : {} Started for {}".format(
                view_name, transaction_id))

            try:
                transaction_obj = youpay_obj.get_youpay_transaction_data(
                    transaction_id)

                self.check_transaction_obj(transaction_obj,
                                           youpay_message_obj)

                self.check_already_verified(transaction_obj,
                                            youpay_message_obj)

            except TransactionAlreadyVerified:
                logger.info("Middleware redirect for transaction_id {}"
                            "".format(transaction_id))
                return JsonResponse(self.response, status=200)

            except TransactionAlreadyProcessed:
                return JsonResponse(self.response, status=404)

            except TransactionNotFound:
                log_message = "TransactionNotFound"
                code = youpay_message_obj.TRANSACTION_NOT_FOUND
                logger.error(log_message)
                self.common_error_response(COMMON_ERROR_MESSAGE_EN, code)
            finally:
                logger.info("Middleware : {} Ended for {}".format(
                    view_name, transaction_id))

    def common_error_response(self, message, code):
        return JsonResponse(
            {
                'errors': {
                    'message': message,
                    'code': code
                }
            },
            status=400)

    def check_already_verified(self, transaction_obj, youpay_message_obj):
        """
        if transaction is already verified, then redirect to success or
        failure url, based on the payment status and approved status
        """

        if transaction_obj.is_payment_verified:
            # Duplicate verification, so redirect to success or failure
            logger.info("Duplicate verification for transaction_id {}".format(
                transaction_obj.transaction_id)
            )
            url_format = '{}?transaction_id={}'
            if transaction_obj.payment_status in SUCCESS_REDIRECT_STATUS_LIST:
                # success page direction on duplicate check
                redirect_url = (
                    url_format.format(
                        transaction_obj.success_url,
                        transaction_obj.transaction_id))
            elif transaction_obj.payment_status in RETRY_END_STATUS_LIST:
                logger.info(
                    "Older retry transaction verify call attempted again for"
                    " transaction {}".format(transaction_obj.transaction_ids))
                raise TransactionAlreadyProcessed
            else:
                redirect_url = (
                    url_format.format(
                        transaction_obj.failure_url,
                        transaction_obj.transaction_id))
            self.response = {
                "is_redirect": True,
                "redirect_url": redirect_url,
                "is_success": True,
                "message": youpay_message_obj.MESSAGE.get(
                    youpay_message_obj.DUPLICATE_PAYMENT_VERIFICATION),
                "code": youpay_message_obj.DUPLICATE_PAYMENT_VERIFICATION
            }
            raise TransactionAlreadyVerified()

    def check_transaction_obj(self, transaction_obj, youpay_message_obj):
        if transaction_obj is None:
            raise TransactionNotFound(
                youpay_message_obj.TRANSACTION_NOT_FOUND)
