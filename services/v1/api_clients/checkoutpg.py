from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from core.response_messages import YouPayResponse
from rest_framework.response import Response
from rest_framework import status
from services.constants import TOKEN_TYPE_SAVED_CARD, TOKEN_TYPE_CARD

from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager


class SavedCardPayment(APIView):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        method for handling saved card payment
        """
        # TODO - fetch transaction data from the YouPayTransactionData
        #  - add data into the payment_data
        payment_data = {'token_type': TOKEN_TYPE_SAVED_CARD,
                        'request_data': request.data}
        checkout = CheckoutpgManager()
        response_data = checkout.saved_card_payment(payment_data)
        data = self.response_obj.get_success_dict(
            code=self.response_obj.SUCCESS,
            success_dict=response_data
        )

        return Response(data,
                        status=status.HTTP_200_OK)


class CardPayment(APIView):

    def post(self, request):
        """
        method for card payment
        """
        payment_data = {'token_type': TOKEN_TYPE_CARD,
                        'request_data': request.data}
        checkout = CheckoutpgManager()
        checkout.saved_card_payment(payment_data)
        return Response({},
                        status=status.HTTP_200_OK)


class CheckoutVerification(APIView):
    def get(self, request, *args, **kwargs):
        """method for redirection from the checkout and verify
         the payment from the checkoutpg"""
        return Response({},
                        status=status.HTTP_200_OK)
