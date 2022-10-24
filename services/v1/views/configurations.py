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
    get_payment_options, get_announcements,
    get_session_id_from_header
)

logger = logging.getLogger(__name__)


class ConfigViewSet(ViewSet):
    """
    Config viewset for getting payment gateways with transaction id
    """
    response_obj = YouPayResponse()

    def list(self, request):
        queryset = PaymentGateway.objects.all()
        serializer = PaymentGatewaySerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Method for getting payment options and announcements
        session id is required in header
        transaction id is required in query params
        """

        session_id = get_session_id_from_header(request)

        checkout_obj = CheckoutpgManager()
        try:
            transaction = YouPayTransactionData.objects.get(
                transaction_id=pk)
            if transaction:
                checkout_config, status_code = (
                    checkout_obj.get_configurations(transaction.currency)
                )

                logger.info(
                    "checkoutpg response : {}, {}".format(checkout_config,
                                                          status_code))
                if transaction.session_id == session_id:
                    client = APIClient.objects.get(
                        id=transaction.api_client_id)
                    if client:
                        serializer = PaymentGatewaySerializer(
                            client.payment_gateway.filter(is_active=True),
                            many=True
                        )
                        payment_options = get_payment_options(serializer)
                        announcements_dict = get_announcements()
                        response_data = {
                            "data": {
                                "payment_options": payment_options,
                                "checkoutpg_config": checkout_config,
                                "amount": transaction.amount,
                                "currency": transaction.currency,
                                "service_fee": transaction.service_fee,
                                "vat_amount": transaction.VAT_amount,
                                "base_amount": transaction.base_amount,
                                "announcements": announcements_dict
                            },
                            "integration_response": {
                                "checkoutpg": {
                                    "config": checkout_config,
                                    "status_code": status_code
                                }
                            }
                        }
                        data = self.response_obj.get_success_dict(
                            code=status_code,
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
        finally:
            logger.info(
                "ConfigViewSet retrieve method called, Response data :"
                " {}".format(data))
