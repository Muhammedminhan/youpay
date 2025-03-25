import logging
import urllib.parse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.utils import get_channel_code
from services.v1.views.common import YouPayTransactionCRUD, ClientValidator

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
            channel_code = get_channel_code(client)

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
