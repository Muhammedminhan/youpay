import json
import logging

from django.http import JsonResponse

from core.constants import YOUPAY_PAYMENT_PATHS
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
        print("Middleware worked")

        payment_paths = YOUPAY_PAYMENT_PATHS

        if request.path in payment_paths and request.method == "POST":
            # Middleware check for payment paths with POST method

            data = json.loads(request.body)

            # check transaction status
            transaction_id = decrypt_string(data.get('transaction_id', None))

            obj = YouPayTransactionCRUD()

            transaction_obj = obj.get_youpay_transaction_data(transaction_id)

            transaction_status = transaction_obj.payment_status

            if transaction_status == PAYMENT_STATUS_CANCELLED:
                transaction_message = (
                    "Transaction Failed : You are trying to pay for a "
                    "cancelled transaction. Please try again.")

                logger.error(transaction_message + str(transaction_id))

                redirect_url = (transaction_obj.cancel_url +
                                '?transaction_id=' + transaction_id)

                # Prepairing response data as per the payment API response
                data = {
                    "status": 200,
                    "is_redirect": True,
                    "redirect_url": redirect_url,
                    "message": transaction_message,
                    "code": 1000,
                }

                return JsonResponse(data, status=200)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        print("Process request ", request)
        print("Process view_func ", view_func)
        print("Process view_args ", view_args)
        print("Process view_kwargs ", view_kwargs)
        
        # get view name
        print("View name ", view_func.__name__)
        
        special_marker = getattr(view_func, 'special_marker', False)
        if special_marker:
            # Do something
            print("Special marker found")
            return JsonResponse({"Status": True, })
            
        else:
            print("Special marker not found")

