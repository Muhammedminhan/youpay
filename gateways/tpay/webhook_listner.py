import logging
import hmac
import hashlib
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.constants import PAYMENT_STATUS_DECLINED, PAYMENT_STATUS_PAID
from services.constants import (TPAY_PUBLIC_KEY, TPAY_PRIVATE_KEY,
                                TPAY_SUCCESS_CODES)

logger = logging.getLogger(__name__)


class TPayWebhookListener(APIView):

    def post(self, request):
        request_data = request.data
        status_code = request_data.get("paymentTransactionStatusCode")
        order_info = request_data.get("orderInfo")

        logger.info(f"TPAY webhook received for order {order_info} with "
                    f"status: {status_code}")

        # Verify Digest (Mandatory for TPay Security)
        if not self.verify_digest(request_data):
            logger.error(f"TPAY Webhook authentication failed for order "
                         f"{order_info}")
            return Response({"message": "Bad signature"},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            if status_code in TPAY_SUCCESS_CODES:
                handle_tpay_payment_success(request_data)
            else:
                handle_tpay_payment_failure(request_data)

            return Response(
                {"message": "Webhook processed", "status": True},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error processing TPAY webhook {order_info}: {e}",
                         exc_info=True)
            return Response(
                {"message": "Webhook error", "status": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def verify_digest(self, data):
        """
        Implementation of Digest calculation
        """
        message = (
                str(data.get('action', '')) +
                str(data.get('paymentTransactionStatusCode', '')) +
                str(data.get('transactionId', '')) +
                str(data.get('msisdn', '')) +
                str(data.get('amount', '')) +
                str(data.get('currencyCode', '')) +
                str(data.get('productCatalogName', '')) +
                str(data.get('productId', '')) +
                str(data.get('orderInfo', '')) +
                str(data.get('paymentProviderCode', ''))
        )

        digest = hmac.new(
            TPAY_PRIVATE_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        expected_signature = f"{TPAY_PUBLIC_KEY}:{digest}"
        return hmac.compare_digest(expected_signature, data.get('digest', ''))


def handle_tpay_payment_success(data):
    """
    Logic for successful TPAY payment
    """
    from services.v1.views.common import YouPayTransactionCRUD
    from tabbypgclient.utils import wait_redis_lock

    order_info = data.get('orderInfo')
    lock_name = f'lock:tpay_webhook:order_{order_info}'

    with (wait_redis_lock(lock_name=lock_name)):
        crud = YouPayTransactionCRUD()
        transaction_obj = (
            crud.get_youpay_transaction_data_with_payment_reference(
                order_info))

        if transaction_obj and not transaction_obj.is_payment_verified:
            transaction_obj.payment_status = PAYMENT_STATUS_PAID
            transaction_obj.additional_reference = data.get('transactionId')
            transaction_obj.is_payment_verified = True
            transaction_obj.approved = True
            transaction_obj.response_summary = data.get(
                'paymentTransactionStatusCode')
            transaction_obj.save()
            logger.info(
                f"TPAY Transaction {order_info} marked as PAID via Webhook")


def handle_tpay_payment_failure(data):
    """
    Logic for failed TPAY payment
    """
    from services.v1.views.common import YouPayTransactionCRUD
    order_info = data.get('orderInfo')

    crud = YouPayTransactionCRUD()
    transaction_obj = (
        crud.get_youpay_transaction_data_with_payment_reference(order_info))

    if transaction_obj and not transaction_obj.is_payment_verified:
        transaction_obj.payment_status = PAYMENT_STATUS_DECLINED
        transaction_obj.response_summary = data.get(
            'paymentTransactionStatusCode')
        transaction_obj.approved = False
        transaction_obj.save()
        logger.info(f"TPAY Transaction {order_info} marked as DECLINED via "
                    f"Webhook")
