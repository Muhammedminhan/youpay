import hmac
import hashlib
import json
import time
from django.conf import settings
import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import (
    COMMON_ERROR_MESSAGE_EN, IS_SUCCESS
)
from core.messages import TRANSACTION_DOESNT_EXIST
from core.response_messages import YouPayResponse
from core.utils import get_site_domain, decrypt_string
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from integrations.v1.serializers.checkoutpg_payment_request import (
    ApplepayPaymentDataSerializer
)
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import (
    TOKEN_TYPE_APPLEPAY,
    TOKEN_TYPE_SAVED_CARD,
    TOKEN_TYPE_CARD,
    TOKEN_TYPE_PAYPAL, CHECKOUTPG_RESPONSE_MESSAGE_NULL_CODE
)
from services.utils import get_client_channel_code
from services.v1.views.common import (
    YouPayTransactionCRUD,
    ClientValidator
)

logger = logging.getLogger(__name__)


class SavedCardPayment(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request):
        """
        Method for getting saved card list
        """
        try:
            transaction_id = request.GET['transaction_id']
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id)
            )

            if transaction_obj:
                email = transaction_obj.customer_email
                currency = transaction_obj.currency
                client = transaction_obj.api_client
                channel_code = get_client_channel_code(client)

                checkout = CheckoutpgManager()
                response_data = checkout.get_saved_cards(email, currency,
                                                         channel_code)

                data = self.response_obj.get_success_dict(
                    code=YouPayResponse.SUCCESS,
                    success_dict={'data': {"saved_cards": response_data}})
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """
        method for handling saved card payment
        """
        try:
            site_domain = get_site_domain(request)
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'token_type': TOKEN_TYPE_SAVED_CARD,
                                'transaction_data': transaction_data,
                                'transaction_obj': transaction_obj,
                                'request_data': request.data,
                                'site_domain': site_domain,
                                }
                checkout = CheckoutpgManager()
                response_data, code = checkout.saved_card_payment(
                    payment_data)

                if response_data:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    if code == self.response_obj.PRE_AUTH:
                        data = format_checkoutpg_response(data, code)
                    return Response(data,
                                    status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(error_code=code)
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except ObjectDoesNotExist as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        method for deleting saved card
        """
        try:
            card_id = request.GET.get('id')
            if not card_id:
                return Response({'error': 'card ID is required',
                                 'status': status.HTTP_400_BAD_REQUEST})
            checkout = CheckoutpgManager()
            response_data = checkout.delete_saved_card(card_id=card_id)

            data = self.response_obj.get_success_dict(
                code=YouPayResponse.SUCCESS,
                success_dict={'data': response_data})
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CardPayment(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        method for handling card payment
        """
        try:
            site_domain = get_site_domain(request)
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'token_type': TOKEN_TYPE_CARD,
                                'transaction_data': transaction_data,
                                'request_data': request.data,
                                'transaction_obj': transaction_obj,
                                'site_domain': site_domain}
                checkout = CheckoutpgManager()
                response_data, code = checkout.card_payment(
                    payment_data)
                if response_data:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    if code == self.response_obj.PRE_AUTH:
                        data = format_checkoutpg_response(data, code)
                    return Response(data,
                                    status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(error_code=code)
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except ObjectDoesNotExist as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class PaypalPayment(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        method for handling card payment
        """
        try:
            site_domain = get_site_domain(request)
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'token_type': TOKEN_TYPE_PAYPAL,
                                'transaction_data': transaction_data,
                                'request_data': request.data,
                                'site_domain': site_domain}
                checkout = CheckoutpgManager()
                response_data, code = checkout.paypal_payment(
                    payment_data)
                if response_data:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    return Response(data,
                                    status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(error_code=code)
                    return Response(data,
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CheckoutVerification(APIView):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        """method for redirection from the checkout and verify
         the payment from the checkoutpg"""

        try:
            payment_data = {
                'transaction_id': decrypt_string(
                    request.query_params.get('id')),
                'cko_session_id': request.query_params.get(
                    'cko-session-id')}
            checkout = CheckoutpgManager()
            response_data, code = checkout.verify_payment(payment_data)
            if response_data:
                data = self.response_obj.get_success_dict(
                    code=code,
                    success_dict=response_data
                )
                formatted_data = format_checkoutpg_response(data, code)
                return Response(formatted_data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                formatted_data = format_checkoutpg_response(data, code)
                return Response(formatted_data,
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error in CheckoutVerification: {}".format(str(e)),
                         exc_info=True)
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


def format_checkoutpg_response(data, code):
    transaction_message = data.get('transaction_message')
    errors = data.get('errors')
    is_success = data.get(IS_SUCCESS)

    if transaction_message:
        data['code'] = code
        data['message'] = transaction_message.get('response_summary', None)
        data[IS_SUCCESS] = is_success
        data.pop('transaction_message', None)
    if errors:
        errors['message'] = COMMON_ERROR_MESSAGE_EN
        errors['code'] = code

    if not data.get('message'):
        data['message'] = COMMON_ERROR_MESSAGE_EN
        data['code'] = CHECKOUTPG_RESPONSE_MESSAGE_NULL_CODE
    return data


class ApplePayStatusUpdateAPI(YouPayTransactionCRUD, APIView,
                              ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Applepay update status API
        """
        logger.info(
            "ApplePay status update request received. "
            "Headers=%s Payload=%s",
            {
                "X-Signature": request.headers.get("X-Signature"),
                "X-Timestamp": request.headers.get("X-Timestamp"),
            },
            request.data
        )
        if not self.verify_hmac_signature(request):
            return Response(
                {"errors": {"code": 401, "message": "Unauthorized"}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                serializer = ApplepayPaymentDataSerializer(transaction_obj)
                transaction_data = serializer.data

                payment_data = {
                    'transaction_data': transaction_data,
                    'transaction_obj': transaction_obj,
                    'payment_stage': request.data.get('payment_stage'),
                    'status': request.data.get('status'),
                    'token_type': TOKEN_TYPE_APPLEPAY,
                    'request_data': request.data,
                    'response_data': request.data
                }
                checkout = CheckoutpgManager()
                response_data, code = checkout.applepay_update_status(
                    payment_data)
                if code in self.response_obj.APPLEPAY_SUCCESS_CODES:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )

                    formatted_data = self.format_applepay_response(data, code)

                    return Response(formatted_data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_success_dict(
                        code=code,
                        success_dict=response_data
                    )
                    formatted_data = self.format_applepay_response(data, code)

                    return Response(formatted_data,
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST)
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def format_applepay_response(self, data, code):

        transaction_message = data.get('transaction_message')
        errors = data.get('errors')

        if transaction_message:
            data['code'] = code
            data['message'] = transaction_message.get('response_summary',
                                                      None)
            data.pop('transaction_message', None)

        if errors:
            errors['message'] = COMMON_ERROR_MESSAGE_EN
            errors['code'] = code

        return data

    def verify_hmac_signature(self, request):

        if not getattr(settings, 'APPLEPAY_HMAC_SECRET', None):
            logger.error("APPLEPAY_HMAC_SECRET is not configured")
            return False

        received_sig = request.headers.get("X-Signature")
        timestamp = request.headers.get("X-Timestamp")

        if not received_sig or not timestamp:
            logger.error(
                "Missing ApplePay HMAC headers. "
                "signature_present=%s timestamp_present=%s",
                bool(received_sig),
                bool(timestamp)
            )
            return False

        try:
            timestamp_int = int(timestamp)

            if abs(time.time() - timestamp_int / 1000) > 300:
                logger.error(
                    "ApplePay HMAC timestamp expired. timestamp=%s",
                    timestamp
                )
                return False

            payload = request.data.copy()
            payload["timestamp"] = timestamp

            payload_string = json.dumps(
                payload,
                separators=(",", ":"),
                sort_keys=True
            )

            expected_sig = hmac.new(
                settings.APPLEPAY_HMAC_SECRET.encode(),
                payload_string.encode(),
                hashlib.sha256
            ).hexdigest()

            logger.info(
                "ApplePay HMAC debug. "
                "transaction_id=%s payload=%s "
                "received_sig=%s expected_sig=%s",
                request.data.get("transaction_id"),
                payload_string,
                received_sig,
                expected_sig
            )

            if not hmac.compare_digest(received_sig, expected_sig):
                logger.error(
                    "ApplePay HMAC signature mismatch. "
                    "transaction_id=%s",
                    request.data.get("transaction_id")
                )
                return False

            logger.info(
                "ApplePay HMAC validation success. "
                "transaction_id=%s",
                request.data.get("transaction_id")
            )
            return True

        except Exception as e:
            logger.error(
                "ApplePay HMAC verification failed: %s",
                str(e),
                exc_info=True
            )
            return False
