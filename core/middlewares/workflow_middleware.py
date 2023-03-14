import json
import logging

from django.http import JsonResponse

from core.constants import MAX_PAYMENT_RETRY_COUNT
from core.messages import MIDDLEWARE_STATUS_CHECK_MESSAGE
from core.response_messages import YouPayResponse
from payments.constants import PAYMENT_STATUS_CANCELLED, PAYMENT_STATUS_PAID

logger = logging.getLogger(__name__)


class PaymentStatusCheckMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):

        from core.utils import decrypt_string
        payment_status_check = getattr(view_func,
                                       'payment_status_check', False)

        # this will check for only post requests
        if payment_status_check and request.method == 'POST':
            data = json.loads(request.body)
            transaction_id = decrypt_string(data.get('transaction_id', None))

            from services.v1.views.common import (YouPayTransactionCRUD)
            youpay_obj = YouPayTransactionCRUD()

            transaction_obj = youpay_obj.get_youpay_transaction_data(
                transaction_id)

            transaction_status = transaction_obj.payment_status

            # to import youpay codes
            youpay_message_obj = YouPayResponse()

            if transaction_status == PAYMENT_STATUS_PAID:
                """
                This will redirect already paid transaction to success url
                """
                transaction_message = (
                    "Transaction Unsuccessful : You are trying to pay again "
                    "for a successful transaction. ")

                logger.info(transaction_message + str(transaction_id))

                redirect_url = self.get_redirect_url(
                    transaction_obj.success_url, transaction_id)

                # Preparing response data as per the payment API response
                response_data = self.get_payment_response(
                    redirect_url, transaction_message, youpay_message_obj)

                return JsonResponse(response_data, status=200)

            if transaction_status == PAYMENT_STATUS_CANCELLED:
                """
                This will redirect to cancel url, so wont able to pay for
                already canceled transactions
                """

                transaction_message = MIDDLEWARE_STATUS_CHECK_MESSAGE

                logger.info(transaction_message + str(transaction_id))

                redirect_url = self.get_redirect_url(
                    transaction_obj.cancel_url, transaction_id)

                # Preparing response data as per the payment API response
                data = {
                    "is_redirect": True,
                    "redirect_url": redirect_url,
                    "message": transaction_message,
                    "code": youpay_message_obj.MIDDLEWARE_REDIRECTED,
                }

                return JsonResponse(data, status=200)

            if transaction_obj.retry_count >= MAX_PAYMENT_RETRY_COUNT:
                """
                if retry count is more than MAX_RETRY_COUNT, then cancel the 
                transaction and redirect to cancel url
                """

                message = ("Payment Cancelled : Maximum retry count reached"
                           " for transaction id: {} ".format(transaction_id))

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
                    "redirect_url": redirect_url,
                    "message": message,
                    "code": youpay_message_obj.MAX_PAYMENT_ATTEMPT_REACHED,
                }

                return JsonResponse(data, status=200)
            else:

                # avoid retry count increment for applepay authorize and paid
                # transactions
                payment_stage = data.get('payment_stage', None)

                if not (payment_stage == 'authorized' or
                        payment_stage == 'paid'
                        and transaction_obj.payment_method == 'applepay'):

                    retry_count = transaction_obj.retry_count + 1

                    youpay_obj.update_youpay_transaction_data(
                        {
                            "transaction_id": transaction_id,
                            "retry_count": retry_count
                        }
                    )

    def get_payment_response(
            self, redirect_url, transaction_message, youpay_message_obj):
        data = {
            "is_redirect": True,
            "redirect_url": redirect_url,
            "message": transaction_message,
            "code": youpay_message_obj.MIDDLEWARE_REDIRECTED,
        }
        return data

    def get_redirect_url(self, url, transaction_id):
        redirect_url = (url + '?transaction_id=' + transaction_id)
        return redirect_url
