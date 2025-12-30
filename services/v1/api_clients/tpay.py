from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from core.constants import LANGUAGE_ENGLISH
from core.utils import decrypt_string
from services.v1.views.common import (generate_script_signature,
                                      generate_checkout_signature,
                                      get_operator_code, YouPayTransactionCRUD)
from services.constants import TPAY_MERCHANT_TEMPLATE_KEY

logger = logging.getLogger(__name__)


class TPayInitializeAPIView(APIView, YouPayTransactionCRUD):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        transaction_id = request.data.get("transaction_id")
        decrypted_id = decrypt_string(transaction_id)
        logger.info(f"Received TPay payment initialization request for "
                    f"Transaction ID: {decrypted_id}")

        transaction_obj = self.get_youpay_transaction_data(decrypted_id)

        msisdn = request.data.get("msisdn")
        redirect_url = transaction_obj.success_url
        language = transaction_obj.language
        language_code = 1 if language == LANGUAGE_ENGLISH else 2
        order_info = transaction_obj.order_id
        operator_code = get_operator_code(msisdn)
        product_price = transaction_obj.amount
        product_catalog = request.data.get("product_catalog")

        # Script signature
        epoch, script_signature = generate_script_signature()

        # Checkout signature
        checkout_signature = generate_checkout_signature(
            TPAY_MERCHANT_TEMPLATE_KEY,
            msisdn,
            operator_code,
            product_catalog,
            product_price,
            language_code,
            order_info,
            redirect_url
        )

        return Response({
            "epochTimeSpan": epoch,
            "scriptSignature": script_signature,
            "checkoutData": {
                "merchantTemplateKey": TPAY_MERCHANT_TEMPLATE_KEY,
                "msisdn": msisdn,
                "operatorCode": operator_code,
                "productCatalogName": product_catalog,
                "productPrice": product_price,
                "language": language_code,
                "orderInfo": order_info,
                "redirectUrl": redirect_url,
                "signature": checkout_signature
            }
        }, status=status.HTTP_200_OK)
