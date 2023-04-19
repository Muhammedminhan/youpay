import json
import logging

from django.http import JsonResponse

from core.constants import MAX_PAYMENT_RETRY_COUNT
from core.exceptions import (
    TransactionNotFound,
    TransactionAlreadyPaid,
    TransactionAlreadyCancelled)
from core.messages import (
    COMMON_ERROR_MESSAGE_EN, MIDDLEWARE_STATUS_CHECK_MESSAGE,
    MIDDLEWARE_ALREADY_PAID_MESSAGE)
from core.response_messages import YouPayResponse
from payments.constants import (
    PAYMENT_STATUS_CANCELLED, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_METHOD_APPLEPAY)

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
        from core.utils import decrypt_string
        from services.v1.views.common import (YouPayTransactionCRUD)

        youpay_obj = YouPayTransactionCRUD()

        # to import youpay codes
        youpay_message_obj = YouPayResponse()
        log_message = ""
        code = None
        try:
            payment_status_check = getattr(view_func,
                                           'payment_status_check', False)

            # this will check for only post requests
            if payment_status_check and request.method == 'POST':
                data = json.loads(request.body)
                transaction_id = decrypt_string(
                    data.get('transaction_id', None))

                transaction_obj = youpay_obj.get_youpay_transaction_data(
                    transaction_id)

                self.check_transaction_obj(transaction_obj,
                                           youpay_message_obj)

                self.check_transaction_already_paid(transaction_obj,
                                                    youpay_message_obj)

                self.check_transaction_already_cancelled(
                    transaction_obj,
                    youpay_message_obj)

                if transaction_obj.retry_count >= MAX_PAYMENT_RETRY_COUNT:
                    """
                    if retry count is more than MAX_RETRY_COUNT, then cancel 
                    the transaction and redirect to cancel url
                    """

                    message = "You have reached your maximum retry attempt"

                    youpay_obj.update_youpay_transaction_data(
                        {
                            "transaction_id": transaction_id,
                            "payment_status": PAYMENT_STATUS_CANCELLED
                        }
                    )

                    redirect_url = self.get_redirect_url(
                        transaction_obj.cancel_url, transaction_id)

                    # Preparing response data as per the payment API response
                    data = {
                        "is_redirect": True,
                        "is_success": False,
                        "redirect_url": redirect_url,
                        "message": message,
                        "code": youpay_message_obj.MAX_PAYMENT_ATTEMPT_REACHED,
                    }

                    return JsonResponse(data, status=200)

                else:

                    # avoid retry count increment for applepay authorize and paid
                    # transactions
                    payment_stage = data.get('payment_stage', None)

                    if not (payment_stage == PAYMENT_STATUS_AUTHORIZED or
                            payment_stage == PAYMENT_STATUS_PAID
                            and transaction_obj.payment_method ==
                            PAYMENT_METHOD_APPLEPAY):
                        retry_count = transaction_obj.retry_count + 1

                        youpay_obj.update_youpay_transaction_data(
                            {
                                "transaction_id": transaction_id,
                                "retry_count": retry_count
                            }
                        )

        except TransactionAlreadyCancelled:
            return JsonResponse(self.response, status=200)

        except TransactionAlreadyPaid:
            return JsonResponse(self.response, status=200)

        except TransactionNotFound:
            log_message = "TransactionNotFound"
            code = youpay_message_obj.UNKNOWN_ERR
            logger.error(log_message)
            self.common_error_response(COMMON_ERROR_MESSAGE_EN, code)

        except Exception as e:
            log_message = "Exception in middleware: {}".format(e)
            code = youpay_message_obj.UNKNOWN_ERR
            logger.error(log_message)
            self.common_error_response(COMMON_ERROR_MESSAGE_EN, code)

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

    def common_error_response(self, message, code):
        return JsonResponse(
            {
                'errors': {
                    'message': message,
                    'code': code
                }
            },
            status=400)
