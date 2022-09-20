import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from integrations.models import PaymentGateway
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from payments.models import YouPayTransactionData
from services.models import APIClient
from services.v1.serializers.client_registrattion import (
    PaymentGatewaySerializer
)
from services.v1.views.utils import (
    get_session_id_and_transaction_id,
    get_gateways
)

logger = logging.getLogger(__name__)


class ConfigViewSet(ViewSet, CheckoutpgManager):
    """
    Config viewset for getting payment gateways with transaction id
    """
    response_obj = YouPayResponse()

    def list(self, request):
        queryset = PaymentGateway.objects.all()
        serializer = PaymentGatewaySerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        session_id, transaction_id = get_session_id_and_transaction_id(pk)

        try:
            transaction = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)
            if transaction:
                checkout_config, status_code = \
                    self.get_configuratoins(transaction.currency)
                # TODO - check checkout_config, if not get the status code

                if transaction.session_id == session_id:
                    client = APIClient.objects.get(
                        id=transaction.api_client_id)
                    if client:
                        serializer = PaymentGatewaySerializer(
                            client.payment_gateway.filter(is_active=True),
                            many=True
                        )

                        payment_gateways = get_gateways(serializer)

                        response_data = {
                            "data": {
                                "payment_gateways": payment_gateways,
                                "checkoutpg_config": checkout_config,
                                "amount": transaction.amount,
                                "currency": transaction.currency,
                                "service_fee": transaction.service_fee,
                                "vat_amount": transaction.VAT_amount,
                                "base_amount": transaction.base_amount,
                            },
                        }
                        data = self.response_obj.get_success_dict(
                            code=self.response_obj.SUCCESS,
                            success_dict=response_data
                        )

                        return Response(data,
                                        status=status.HTTP_200_OK)
                    else:
                        message = "Client doesn't exists"
                        data = self.response_obj.get_404_message(
                            message=message)

                        return Response(data,
                                        status=status.HTTP_404_NOT_FOUND)
                else:
                    message = "Session expired or doesn't match"
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
