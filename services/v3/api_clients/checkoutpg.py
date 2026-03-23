import logging
import urllib.parse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.utils import get_client_channel_code
from services.v1.views.common import ClientValidator, YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class SavedCardPayment(APIView, YouPayTransactionCRUD, ClientValidator):
    response_obj = YouPayResponse()
    transaction_obj = None

    def get(self, request):
        """
        Method for getting saved card list
        """
        try:
            raw_email = request.query_params.get('customer_email', "")
            customer_uid = request.query_params.get('customer_uid', "")
            email = urllib.parse.unquote(raw_email)
            transaction_id = request.query_params.get('transaction_id')
            if transaction_id:
                self.transaction_obj = self.get_youpay_transaction_data(
                    decrypt_string(transaction_id)
                )
            currency = None
            _, client = self.validate_client(request)
            client_obj = getattr(self.transaction_obj, "api_client", client)
            if not client_obj:
                logger.info(
                    "payment request client validation failed for {0}"
                    .format("order_reference"))
                data = self.response_obj.get_400_message(
                    message="Client Does Not Exist")
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
            if self.transaction_obj:
                email = self.transaction_obj.customer_email
                customer_uid = self.transaction_obj.customer_uid
                currency = self.transaction_obj.currency
            
            channel_code = get_client_channel_code(client_obj)

            checkout = CheckoutpgManager()
            response_data = checkout.get_saved_cards_v3(email, currency,
                                                        channel_code,
                                                        customer_uid,
                                                        client_obj.client_code)

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
            customer_uid = request.query_params.get('customer_uid')
            channel_code = get_client_channel_code(client)

            checkout = CheckoutpgManager()
            response_data = checkout.delete_saved_card_v3(email,
                                                          channel_code,
                                                          customer_uid)

            data = self.response_obj.get_success_dict(
                code=YouPayResponse.SUCCESS,
                success_dict={'data': response_data})
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
