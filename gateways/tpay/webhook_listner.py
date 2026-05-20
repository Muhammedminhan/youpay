import logging
import hmac
import hashlib
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from gateways.tpay.models import TPayWebhookLog
from services.constants import (TPAY_PUBLIC_KEY, TPAY_PRIVATE_KEY)

logger = logging.getLogger(__name__)


class TPayWebhookListener(APIView):

    def get(self, request):
        request_data = request.query_params
        status_code = request_data.get("paymentTransactionStatusCode")
        order_info = request_data.get("orderInfo")

        logger.info(f"TPAY webhook received for order {order_info} with "
                    f"status: {status_code}")

        if not self.verify_digest(request_data):
            logger.error(f"TPAY Webhook authentication failed for order "
                         f"{order_info}")
            return Response({"message": "Bad signature"},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload_dict = dict(request_data)

            TPayWebhookLog.objects.create(
                action=request_data.get('action'),
                payment_transaction_status_code=status_code,
                transaction_id=request_data.get('transactionId'),
                msisdn=request_data.get('msisdn'),
                amount=request_data.get('amount'),
                currency_code=request_data.get('currencyCode'),
                payment_date=request_data.get('paymentDate'),
                product_catalog_name=request_data.get('productCatalogName'),
                product_id=request_data.get('productId'),
                order_info=order_info,
                payment_provider_code=request_data.get('paymentProviderCode'),
                digest=request_data.get('digest'),
                payload=payload_dict
            )

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
        logger.info(f"TPAY received data: {data}")

        message = (
                str(data.get('action', '')) +
                str(data.get('paymentTransactionStatusCode', '')) +
                str(data.get('transactionId', '')) +
                str(data.get('msisdn', '')) +
                str(data.get('amount', '')) +
                str(data.get('currencyCode', '')) +
                str(data.get('paymentDate', '')) +
                str(data.get('productCatalogName', '')) +
                str(data.get('productId', '')) +
                str(data.get('orderInfo', '')) +
                str(data.get('paymentProviderCode', ''))
        )

        logger.info(f"TPAY generated message: {message}")

        digest = hmac.new(
            TPAY_PRIVATE_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        expected_signature = f"{TPAY_PUBLIC_KEY}:{digest}"

        return hmac.compare_digest(
            expected_signature,
            data.get('digest', '')
        )
