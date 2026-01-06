from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, ROUND_HALF_UP
import logging

from core.constants import LANGUAGE_ENGLISH
from core.messages import TRANSACTION_DOESNT_EXIST
from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from services.v1.views.common import (generate_script_signature,
                                      generate_checkout_signature,
                                      get_operator_code, YouPayTransactionCRUD)
from services.constants import TPAY_MERCHANT_TEMPLATE_KEY, TPAY_REDIRECT_URL

logger = logging.getLogger(__name__)


class TPayInitializeAPIView(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            transaction_id = request.data.get("transaction_id")
            decrypted_id = decrypt_string(transaction_id)
            logger.info(
                f"Received TPay payment initialization request for "
                f"Transaction ID: {decrypted_id}"
            )

            transaction_obj = self.get_youpay_transaction_data(decrypted_id)
            if not transaction_obj:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST
                )
                return Response(data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)

            msisdn = request.data.get("msisdn", "")
            product_catalog = request.data.get("product_catalog")
            redirect_url = TPAY_REDIRECT_URL
            language = transaction_obj.language
            language_code = 1 if language == LANGUAGE_ENGLISH else 2
            order_info = transaction_obj.order_id
            operator_code = get_operator_code(msisdn)
            product_price = format(Decimal(str(
                transaction_obj.amount)).quantize(Decimal("0.00"),
                rounding=ROUND_HALF_UP), "f"
            )

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

        except Exception as e:
            logger.error(
                f"Exception occurred while initializing TPay payment: {str(e)}",
                exc_info=True
            )
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
