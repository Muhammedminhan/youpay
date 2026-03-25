from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, ROUND_HALF_UP
import logging

from core.constants import LANGUAGE_ENGLISH, PAYMENT_GATEWAY_TPAY
from core.messages import TRANSACTION_DOESNT_EXIST
from core.response_messages import YouPayResponse
from core.utils import decrypt_string, get_redirect_url
from gateways.common import _get_payment_reference_number
from gateways.tpay.models import TPayTransaction
from integrations.constants import TPAY_HUB_CODE
from integrations.v1.gateway_clients.utils import get_response_url
from payments.constants import (PAYMENT_METHOD_TPAY_ETISALAT,
                                PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
                                PAYMENT_STATUS_DECLINED)
from services.v1.views.common import (generate_script_signature,
                                      generate_checkout_signature,
                                      YouPayTransactionCRUD,
                                      verify_tpay_response_signature,
                                      get_custom_error_code)
from services.constants import (TPAY_MERCHANT_TEMPLATE_KEY,
                                ETISALAT_OPERATOR_CODE,
                                TPAY_PRODUCT_CATALOG_NAME,
                                PAYMENT_STATUS_INITIALIZED,
                                TPAY_STATUS_LABELS)

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
            order_info = _get_payment_reference_number(
                transaction_obj.order_reference)
            operator_code = ETISALAT_OPERATOR_CODE
            product_catalog = TPAY_PRODUCT_CATALOG_NAME

            TPayTransaction.objects.update_or_create(
                payment_reference=order_info,
                defaults={
                    'youpay_transaction': transaction_obj,
                    'msisdn': msisdn,
                    'status': PAYMENT_STATUS_INITIALIZED,
                    'amount': transaction_obj.amount,
                    'currency': transaction_obj.currency,
                    'operator_code': operator_code,
                    'product_catalog': product_catalog
                }
            )

            self.update_youpay_transaction_data({
                'transaction_id': decrypted_id,
                'payment_gateway': PAYMENT_GATEWAY_TPAY,
                'payment_method': PAYMENT_METHOD_TPAY_ETISALAT,
                'payment_status': PAYMENT_STATUS_PENDING,
                'payment_reference': order_info
            })

            redirect_url = get_response_url(transaction_obj,
                is_partial_payment=False, gty_override=TPAY_HUB_CODE)
            language = transaction_obj.language
            language_code = 1 if language == LANGUAGE_ENGLISH else 2
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


class TPayVerifyAPIView(APIView, YouPayTransactionCRUD):
    """
    API view for verifying a TPay payment redirect.
    """
    response_obj = YouPayResponse()

    def get(self, request):
        try:
            transaction_id = request.query_params.get("id")
            decrypted_id = decrypt_string(transaction_id)

            logger.info(f"TPay Verify Redirect received for {decrypted_id} "
                        f"with params: {request.query_params}")

            op_status_code = request.query_params.get("operationStatusCode", "")
            tpay_transaction_id = request.query_params.get("transactionId", "")
            amount_charged = request.query_params.get("amountCharged", "")
            operator_code = request.query_params.get("operatorCode", "")
            msisdn = request.query_params.get("msisdn", "")
            order_info = request.query_params.get("orderInfo", "")
            product_catalog = request.query_params.get("productCatalogName", "")
            language = request.query_params.get("language", "")
            error_message = request.query_params.get("errorMessage", "")
            checkout_id = request.query_params.get("checkoutId", "")
            received_signature = request.query_params.get("signature", "")

            logger.info(f"Verifying TPay payment for Transaction: "
                        f"{decrypted_id}, TPay ID: {tpay_transaction_id}")

            transaction_obj = self.get_youpay_transaction_data(decrypted_id)
            if not transaction_obj:
                return Response(self.response_obj.get_404_message(
                    TRANSACTION_DOESNT_EXIST), status=status.HTTP_400_BAD_REQUEST)

            # Verify Signature (Security Check)
            is_valid = verify_tpay_response_signature(
                op_status_code, tpay_transaction_id, amount_charged, operator_code,
                msisdn, order_info, product_catalog, language, error_message,
                checkout_id, received_signature
            )

            tpay_tx = TPayTransaction.objects.filter(
                payment_reference=order_info).first()
            if tpay_tx:
                tpay_tx.tpay_transaction_id = tpay_transaction_id if (
                    tpay_transaction_id) else None
                tpay_tx.status = TPAY_STATUS_LABELS.get(op_status_code, op_status_code)
                tpay_tx.raw_response = request.query_params
                tpay_tx.save()

            custom_code, is_success = get_custom_error_code(op_status_code)
            custom_message = self.response_obj.MESSAGE.get(custom_code)

            if not is_valid:
                logger.error(f"TPay Signature mismatch for transaction "
                             f"{decrypted_id}")
                redirect_url = get_redirect_url(transaction_obj.failure_url,
                                                str(decrypted_id))
                return Response({
                    "status": 400,
                    "is_redirect": True,
                    "is_success": False,
                    "redirect_url": redirect_url,
                    "message": custom_message,
                    "code": custom_code
                }, status=status.HTTP_400_BAD_REQUEST)

            payment_data_update = {
                'transaction_id': decrypted_id,
                'response_summary': error_message
            }

            if is_success:
                redirect_url = get_redirect_url(transaction_obj.success_url,
                                                str(decrypted_id))
                payment_data_update['payment_status'] = PAYMENT_STATUS_PAID
                payment_data_update['approved'] = True
                payment_data_update['is_payment_verified'] = True
                self.update_youpay_transaction_data(payment_data_update)

                return_data = {
                    "status": 200,
                    "is_redirect": True,
                    "is_success": True,
                    "redirect_url": redirect_url,
                    "message": custom_message,
                }

                return Response(self.response_obj.get_success_dict(
                    code=self.response_obj.SUCCESS,
                    success_dict=return_data
                ), status=status.HTTP_200_OK)

            else:
                redirect_url = get_redirect_url(transaction_obj.failure_url,
                                                str(decrypted_id))
                payment_data_update.update({
                    'payment_status': PAYMENT_STATUS_DECLINED,
                    'approved': False,
                    'is_payment_verified': True
                })
                self.update_youpay_transaction_data(payment_data_update)

                return_data = {
                    "status": 200,
                    "code": custom_code,
                    "is_redirect": True,
                    "is_success": False,
                    "redirect_url": redirect_url,
                    "message": custom_message
                }
                return Response(return_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error verifying TPay payment: {str(e)}",
                         exc_info=True)
            return Response(self.response_obj.get_400_message(message=str(
                e)).get('errors'), status=status.HTTP_400_BAD_REQUEST)
