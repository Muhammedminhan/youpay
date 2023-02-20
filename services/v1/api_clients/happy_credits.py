import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import get_site_domain, decrypt_string
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.v1.views.common import YouPayTransactionCRUD
from integrations.v1.gateway_clients.happy_credits import HappyCreditsManager

logger = logging.getLogger(__name__)


class HappyCreditsCreditBalance(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def get(self, request, *args, **kwargs):
        """
        Method for fetching credit balance from happy credits
        """
        try:
            transaction_id = request.query_params.get('id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))
            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                request_data = {'transaction_data': transaction_data}
                happy_credits = HappyCreditsManager()
                response_data, code = happy_credits.get_credit_balance(
                    request_data)
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
                    message="Transaction doesn't exists for happy credits")
                return Response(data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)
