# create session class here
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import decrypt_string, get_site_domain
from integrations.v1.gateway_clients.tabbypg import TabbyPGManager
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.v1.views.common import (
    YouPayTransactionCRUD, ClientValidator)


class CreateSession(YouPayTransactionCRUD, APIView, ClientValidator):
    response_obj = YouPayResponse()

    def post(self, request):
        try:
            site_domain = get_site_domain(request)
            transaction_id = request.data.get('transaction_id')

            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {
                    'transaction_data': transaction_data,
                    'request_data': "request.data",
                    "language": "en",
                    "loyality_level": "0",
                    'site_domain': site_domain}

                tabbypg = TabbyPGManager()
                response_data, code = tabbypg.create_session(
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
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
