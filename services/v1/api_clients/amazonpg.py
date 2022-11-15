import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.response_messages import YouPayResponse
from core.utils import get_site_domain, decrypt_string
from integrations.v1.gateway_clients.amazonpg import AmazonPGManager
from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer
)
from services.v1.views.common import YouPayTransactionCRUD

logger = logging.getLogger(__name__)


class AmazonPGAuthentication(APIView, YouPayTransactionCRUD):
    response_obj = YouPayResponse()

    def post(self, request):
        """
        Method for handling amazonpg authentication api
        """
        try:
            transaction_id = request.data.get('transaction_id')
            transaction_obj = self.get_youpay_transaction_data(
                decrypt_string(transaction_id))

            if transaction_obj:
                serializer = YouPayTransactionDataSerializer(transaction_obj)
                transaction_data = serializer.data
                payment_data = {'transaction_data': transaction_data,
                                'request_data': request.data}
                amazon_pay = AmazonPGManager()
        except Exception as e:
            data = self.response_obj.get_400_message(message=str(e))
            return Response(data.get('errors'),
                            status=status.HTTP_400_BAD_REQUEST)