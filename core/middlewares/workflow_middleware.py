import json
import logging

from django.http import JsonResponse

from core.utils import decrypt_string
from payments.constants import PAYMENT_STATUS_CANCELLED
from services.v1.views.common import (YouPayTransactionCRUD)

logger = logging.getLogger(__name__)


class WorkflowCheckMiddleware(object):
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

        cancelled_payment_check = getattr(view_func,
                                          'cancelled_payment_check', False)
        if cancelled_payment_check:
            # Do something
            print("Cancell Payment Check \n\n\n")

            data = json.loads(request.body)

            # check transaction status
            transaction_id = decrypt_string(data.get('transaction_id', None))

            youpay_obj = YouPayTransactionCRUD()

            transaction_obj = youpay_obj.get_youpay_transaction_data(
                transaction_id)

            transaction_status = transaction_obj.payment_status

            print("----------------- TRANSACTION STATUS ", transaction_status)

            if transaction_status == PAYMENT_STATUS_CANCELLED:
                """
                This will redirect to cancel url, so wont able to pay for
                already canceled transactions
                """

                transaction_message = (
                    "Transaction Failed : You are trying to pay for a "
                    "cancelled transaction. Please try again.")

                logger.error(transaction_message + str(transaction_id))

                redirect_url = (transaction_obj.cancel_url +
                                '?transaction_id=' + transaction_id)

                # Preparing response data as per the payment API response
                data = {
                    "status": 200,
                    "is_redirect": True,
                    "redirect_url": redirect_url,
                    "message": transaction_message,
                    "code": 1000,
                }

                return JsonResponse(data, status=200)
