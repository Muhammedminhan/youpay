from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from payments.models import YouPayTransactionData
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import TOKEN_TYPE_CARD
from services.constants import TOKEN_TYPE_SAVED_CARD


class SavedCardPayment(APIView):
    response_obj = YouPayResponse()

    def get(self, request):
        """
        Method for getting saved card list
        """
        try:
            transaction_id = request.GET['transaction_id']

            transaction_obj = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)
            if transaction_obj:
                email = transaction_obj.customer_email
                currency = transaction_obj.currency

                checkout = CheckoutpgManager()
                response_data = checkout.get_saved_cards(email, currency)

                data = self.response_obj.get_success_dict(
                    code=YouPayResponse.SUCCESS,
                    success_dict={'data': {"saved_cards": response_data}})
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_404_message(
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """
        method for handling saved card payment
        """
        # TODO - fetch transaction data from the YouPayTransactionData
        #  - add data into the payment_data
        try:
            transaction_id = request.data.get('transaction_id')
            is_save_user_token = request.data.get('is_save_user_token')
            response_url = request.data.get('response_url')
            cvv = request.data.get('cvv')
            card_type = request.data.get('card_type')
            token = request.data.get('token')
            channel_code = request.data.get('channel_code')
            invoice_pk = request.data.get('invoice_pk')
            customer_ip_address = request.data.get('customer_ip_address')
            customer_name = request.data.get('customer_name')
            transaction_obj = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'token_type': TOKEN_TYPE_SAVED_CARD,
                                'transaction_data': transaction_data,
                                'request_data': request.data}
                checkout = CheckoutpgManager()
                response_data = checkout.saved_card_payment(payment_data)
                data = self.response_obj.get_success_dict(
                    code=self.response_obj.SUCCESS,
                    success_dict=response_data
                )
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_404_message(
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        method for deleting saved card
        """
        try:
            card_id = request.GET['card_id']

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
