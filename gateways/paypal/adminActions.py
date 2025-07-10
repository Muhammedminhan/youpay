from django.contrib import messages

from core.response_messages import YouPayResponse
from gateways.paypal.constants import PAYPAL_CAPTURE_STATUS_COMPLETED
from gateways.paypal.integrations import PaypalManager


def refund_selected_paypal_transactions(modeladmin, request, queryset):
    try:
        if queryset.count() != 1:
            messages.error(request,
                           "Please select exactly one transaction to refund.")
            return
        obj = queryset.first()

        if not obj.capture_id:
            messages.warning(request,
                             f"Transaction {obj.order_id} has no capture_id.")
            return

        if obj.status != PAYPAL_CAPTURE_STATUS_COMPLETED:
            messages.warning(request,
                             f"Transaction {obj.order_id} has not been captured.")

        request_data = {
            "reference_id": obj.payment_reference,
            "transaction_id": obj.youpay_transaction.transaction_id,
            "transaction_obj": obj.youpay_transaction,
            "paypal_transaction": obj
        }
        response_object = YouPayResponse()
        handler = PaypalManager()
        response, code = handler.refund_paypal_transaction(request_data)

        if code == response_object.SUCCESS:
            messages.success(request, f"Refund successful for {obj.order_id}")
        else:
            messages.error(request,
                           f"Refund failed for {obj.order_id}: {response}")
    except Exception as e:
        messages.error(request, f"Error refunding {obj.order_id}: {str(e)}")
