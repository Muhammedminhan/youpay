import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.messages import REDIRECT_URL, IS_REDIRECT
from core.messages import TRANSACTION_DOESNT_EXIST
from core.response_messages import YouPayResponse
from core.utils import get_site_domain, decrypt_string
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.constants import TOKEN_TYPE_SAVED_CARD, TOKEN_TYPE_CARD, \
    TOKEN_TYPE_PAYPAL
from services.v1.views.common import YouPayTransactionCRUD

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

                checkout = CheckoutpgManager()
                response_data = checkout.get_saved_cards(email, currency)

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
                    return Response(data,
                                    status=status.HTTP_200_OK)
                else:
                    data = self.response_obj.get_error_dict(error_code=code)
                    data[IS_REDIRECT] = True
                    data[REDIRECT_URL] = transaction_data.get('failure_url')
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
                                'site_domain': site_domain}
                checkout = CheckoutpgManager()
                response_data, code = checkout.card_payment(
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
                    data[IS_REDIRECT] = True
                    data[REDIRECT_URL] = transaction_data.get('failure_url')
                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)
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
                    data[IS_REDIRECT] = True
                    data[REDIRECT_URL] = transaction_data.get('failure_url')
                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)
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
                return Response(data,
                                status=status.HTTP_200_OK)
            else:
                data = self.response_obj.get_error_dict(error_code=code)
                return Response(data,
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error in CheckoutVerification: {}".format(str(e)))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
