import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.models import PaymentGateway
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from payments.constants import (
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_ERROR,
    PAYMENT_STATUS_REJECTED,
    PAYMENT_STATUS_VOIDED,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_FLAGGED
)
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.list_failure_statuses = [
            PAYMENT_STATUS_ERROR,
            PAYMENT_STATUS_REJECTED,
            PAYMENT_STATUS_VOIDED,
            PAYMENT_STATUS_CANCELLED,
            PAYMENT_STATUS_FLAGGED
        ]

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

        decrypted_transaction_id = decrypt_string(pk)

        try:
            transaction = YouPayTransactionData.objects.get(
                transaction_id=decrypted_transaction_id)
            if transaction:

                # Redirect to success url if transaction is already paid
                if (
                        transaction.payment_status == PAYMENT_STATUS_PAID or
                        transaction.payment_status in self.list_failure_statuses
                ):
                    return_response = self.retrieve_response(
                        payment_options=None,
                        checkoutpg_config=None,
                        transaction=transaction,
                        announcements_dict=None,
                        status_code=None
                    )
                    data = self.response_obj.get_success_dict(
                        code=self.response_obj.SUCCESS,
                        success_dict=return_response
                    )
                    return Response(data, status=status.HTTP_200_OK)

                checkout_config, status_code = (
                    checkout_obj.get_configurations(transaction.currency)
                )

                logger.info(
                    "checkoutpg response : {}, {}".format(checkout_config,
                                                          status_code))

                # bypass session checking when api client is inactive
                if not transaction.api_client.is_active:
                    session_id = transaction.session_id

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
                        response_data = self.retrieve_response(
                            payment_options=payment_options,
                            checkoutpg_config=checkout_config,
                            transaction=transaction,
                            announcements_dict=announcements_dict,
                            status_code=status_code
                        )

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

    def retrieve_response(self, **kwargs):

        payment_options = kwargs.get('payment_options', None)
        checkoutpg_config = kwargs.get('checkoutpg_config', None)
        transaction = kwargs.get('transaction', None)
        announcements_dict = kwargs.get('announcements_dict', None)
        status_code = kwargs.get('status_code', None)

        amount = None
        currency = None
        service_fee = None
        VAT_amount = None
        base_amount = None
        redirect_url = None

        if transaction:
            amount = transaction.amount
            currency = transaction.currency
            service_fee = transaction.service_fee
            VAT_amount = transaction.VAT_amount
            base_amount = transaction.base_amount

            if transaction.payment_status == PAYMENT_STATUS_PAID:
                redirect_url = transaction.success_url

            if transaction.payment_status in self.list_failure_statuses:
                redirect_url = transaction.failure_url

        response_data = {
            "data": {
                "payment_options": payment_options,
                "checkoutpg_config": checkoutpg_config,
                "amount": amount,
                "currency": currency,
                "service_fee": service_fee,
                "vat_amount": VAT_amount,
                "base_amount": base_amount,
                "redirect_url": redirect_url,
                "announcements": announcements_dict
            },
            "integration_response": {
                "checkoutpg": {
                    "config": checkoutpg_config,
                    "status_code": status_code
                }
            }
        }

        return response_data
