import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.response_messages import YGPayResponse
from integrations.models import PaymentGateway
from payments.models import YGPayTransactionData
from services.models import APIClient
from services.v1.serializers.client_registrattion import \
    PaymentGatewaySerializer

logger = logging.getLogger(__name__)


class ConfigViewSet(ViewSet):
    """
    Config viewset for getting payment gateways with transaction id
    """
    
    response_obj = YGPayResponse()

    def list(self, request):
        queryset = PaymentGateway.objects.all()
        serializer = PaymentGatewaySerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):

        try:
            transaction = YGPayTransactionData.objects.get(
                transaction_id=pk)
            if transaction:
                client = APIClient.objects.get(id=transaction.api_client_id)
                if client:
                    serializer = PaymentGatewaySerializer(
                        client.payment_gateway.filter(is_active=True),
                        many=True
                    )
                    response_data = {"data": serializer.data, }
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=response_data
                    )

                    return Response(data,
                                    status=status.HTTP_200_OK)
                else:
                    message = "Client doesn't exists"
                    data = self.response_obj.get_404_message(message=message)

                    return Response(data,
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                data = self.response_obj.get_error_dict(
                    error_code=self.response_obj.UNKNOWN_ERR)
                return Response(data.get('errors'),
                                status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            data = self.response_obj.get_404_message(message=str(e))
            return Response(
                data,
                status=status.HTTP_404_NOT_FOUND)
