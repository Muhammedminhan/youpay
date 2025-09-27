import logging
import urllib.parse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.utils import get_client_channel_code
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator
from core.utils import decrypt_string
from payments.constants import PAYMENT_OPTION_CARD, PAYMENT_STATUS_PENDING
from core.messages import TRANSACTION_DOESNT_EXIST
from core.constants import PAYMENT_GATEWAY_CHECKOUTPG

logger = logging.getLogger(__name__)

class SavedCardPayment(APIView, YouPayTransactionCRUD, ClientValidator):
    response_obj = YouPayResponse()

    def get(self, request):
        """
        Method for getting saved card list
        """
        try:
            validate, client = self.validate_client(request)
            if not validate:
                logger.info(
                    "payment request client validation failed for {0}"
                    .format("order_reference"))
                data = self.response_obj.get_400_message(
                    message="Client Does Not Exist")
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

            raw_email = request.query_params.get('customer_email')
            email = urllib.parse.unquote(raw_email)
            currency = None
            channel_code = get_client_channel_code(client)

            checkout = CheckoutpgManager()
            response_data = checkout.get_saved_cards(email, currency,
                                                     channel_code)

            data = self.response_obj.get_success_dict(
                code=YouPayResponse.SUCCESS,
                success_dict={'data': {"saved_cards": response_data}})
            return Response(data, status=status.HTTP_200_OK)


        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        method for deleting saved card
        """
        try:
            validate, client = self.validate_client(request)
            if not validate:
                logger.info(
                    "payment request client validation failed for {0}"
                    .format("order_reference"))
                self.return_data = self.response_obj.get_400_message(
                    message="Client Does Not Exist")
                return Response(self.return_data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
            email = request.query_params.get('email')
            channel_code = get_client_channel_code(client)

            checkout = CheckoutpgManager()
            response_data = checkout.delete_saved_card_v2(email,
                                                          channel_code)

            data = self.response_obj.get_success_dict(
                code=YouPayResponse.SUCCESS,
                success_dict={'data': response_data})
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class CreatePaymentSession(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Method for creating payment session
        """
        try:
            transaction_id = request.data.get('transaction_id')
            is_partial_payment = request.data.get('is_partial_payment', False)

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id)
            )

            if transaction_obj:
                checkout = CheckoutpgManager()

                response_data, status_code = (
                    checkout.get_payment_session(transaction_obj))

                if status_code == checkout.SUCCESS and response_data:
                    reference = response_data.get('reference_id')
                    if not is_partial_payment:
                        transaction_data = {
                            "transaction_id": transaction_obj.transaction_id,
                            "payment_reference": reference,
                            "channel_code": response_data.get('channel_code'),
                            "payment_method": PAYMENT_OPTION_CARD,
                            "payment_status": PAYMENT_STATUS_PENDING,
                            "payment_gateway": PAYMENT_GATEWAY_CHECKOUTPG,
                        }
                        self.update_youpay_transaction_data(transaction_data)
                    else:
                        transaction_obj.additional_reference = reference
                        transaction_obj.save()
                        logger.info(f"Saving session reference: {reference}")

                    response_data.pop('channel_code', None)
                    response_data.pop('reference_id', None)
                    response_data.pop('status', None)

                    data = self.response_obj.get_success_dict(
                        code=YouPayResponse.SUCCESS,
                        success_dict={'data': response_data}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_400_message(
                        message="Failed to create payment session"
                    )
                    return Response(data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST
                )
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.exception("Error in CreatePaymentSession.get")
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class SubmitPaymentSession(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Method for submitting payment session
        """
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id)
            )

            if transaction_obj:
                checkout = CheckoutpgManager()
                response_data, status_code = checkout.submit_payment_session(
                    transaction_obj, request.data
                )
                if status_code == checkout.SUCCESS and response_data:
                    response_data.pop('reference_id', None)
                    data = self.response_obj.get_success_dict(
                        code=YouPayResponse.SUCCESS,
                        success_dict={'data': response_data}
                    )
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_400_message(
                        message="Failed to submit payment session"
                    )
                    return Response(data.get('errors'),
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                data = self.response_obj.get_404_message(
                    message=TRANSACTION_DOESNT_EXIST
                )
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.exception("Error in SubmitPaymentSession.post")
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
