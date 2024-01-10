import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.v1.gateway_clients.amazonpg import AmazonPGManager
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.v1.views.common import (
    YouPayTransactionCRUD)

logger = logging.getLogger(__name__)


class AmazonPGTokenization(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Method for handling amazonpg tokenization api
        """
        try:

            transaction_id = decrypt_string(
                request.data.get('transaction_id'))
            transaction_obj = self.get_youpay_transaction_data(transaction_id)
            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                tokenization_data = {
                    'request_data': request.data,
                    'transaction_data': transaction_data
                }
                amazon_pay = AmazonPGManager()
                response_data, code = amazon_pay.tokenization(
                    tokenization_data)

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
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error in AmazonPGTokenization: {}".format(str(e)))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class AmazonPGAuthentication(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Method for handling amazonpg authentication api
        """
        transaction_id = None
        try:
            logger.info(
                "AmazonPGAuthentication API called with request data: {}".format(
                    request.data))
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'transaction_data': transaction_data,
                                'request_data': request.data}
                amazon_pay = AmazonPGManager()
                response_data, code = amazon_pay.payment_authentication(
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
                    message="Transaction doesn't exists")
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            logger.error(
                "AmazonPGAuthentication api failed with error {}, "
                "for transaction {}".format(str(e), transaction_id))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)


class AmazonPGVerification(APIView):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        """
        method for redirection from the checkout and verify
        the payment from the amazonpg
        """

        try:
            payment_data = {
                'transaction_id': decrypt_string(
                    request.query_params.get('id')),
                'payment_reference': request.query_params.get('payment_id')
            }

            amazonpg = AmazonPGManager()
            response_data, code = amazonpg.verify_payment(payment_data)

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
            logger.error("Error in AmazonPGVerification: {}".format(str(e)))
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
