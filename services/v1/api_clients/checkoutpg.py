from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from services.constants import TOKEN_TYPE_SAVED_CARD
from services.v1.constants import CHECKOUTPG_CARD_KEYWORDS, \
    CHECKOUTPG_LIST_CARD


class CheckoutpgCommunicationView(APIView):
    """API endpoint that allows users to be viewed or edited."""
    checkoutpg_obj = CheckoutpgManager()

    response_obj = YouPayResponse()

    def command(self, request, keyword):
        if keyword == CHECKOUTPG_LIST_CARD:
            return self.checkoutpg_obj.get_configuratoins(currency="AED")
        else:
            return self.response_obj.get_400_message(
                message="Invalid keyword")

    def get(self, request, keyword):
        try:
            if keyword not in CHECKOUTPG_CARD_KEYWORDS:
                data = self.response_obj.get_400_message(
                    message="Invalid keyword")
                return Response(data.get('errors'),
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                api_response = self.command(request, keyword)
                data = self.response_obj.get_success_dict(
                    code=YouPayResponse.SUCCESS,
                    success_dict={'data': api_response})

                return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class SavedCardPayment(APIView):
    response_obj = YouPayResponse()

    # TODO - add get method for fetching saved cards, get method

    def post(self, request):
        """
        method for handling saved card payment
        """
        # TODO - fetch transaction data from the YouPayTransactionData
        #  - add data into the payment_data
        payment_data = {'token_type': TOKEN_TYPE_SAVED_CARD,  #
                        'request_data': request.data}
        checkout = CheckoutpgManager()
        response_data = checkout.saved_card_payment(payment_data)
        data = self.response_obj.get_success_dict(
            code=self.response_obj.SUCCESS,
            success_dict=response_data
        )

        return Response(data,
                        status=status.HTTP_200_OK)
    # TODO - add delete method for delete saved cards


class CardPayment(APIView):

    def __int__(self):
        self.payment_data = {}

    def post(self, request):
        """
        method for card payment
        """
        self.payment_data['token_type'] = 'card'
        self.payment_data['request_data'] = request.data
        checkout = CheckoutpgManager()
        checkout.saved_card_payment(self.payment_data)
        status = True
        return status
