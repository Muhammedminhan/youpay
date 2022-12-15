import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from core.utils import decrypt_string
from integrations.models import PaymentGateway
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from integrations.v1.gateway_clients.tabbypg import TabbyPGManager
from payments.constants import (
    PAYMENT_STATUS_ERROR,
    PAYMENT_STATUS_REJECTED,
    PAYMENT_STATUS_VOIDED,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_FLAGGED,
    PAYMENT_STATUS_PAID
)
from payments.models import YouPayTransactionData
from services.models import APIClient
from services.v1.serializers.client_registrattion import (
    PaymentGatewaySerializer
)
from services.v1.views.utils import (get_payment_options, get_announcements,
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
        tabbypg_obj = TabbyPGManager()

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
                tabbypg_config = self.get_tabby_conf(
                    tabbypg_obj.tabbypg_config)

                logger.info(
                    "checkoutpg response : {}, {}".format(checkout_config,
                                                          status_code))

                # bypass session checking when api client is inactive
                if not transaction.api_client.validate_session:
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
                        b2c_payback_obj = B2CPaybackManager()
                        payback_config = b2c_payback_obj.get_configurations(
                            transaction.amount, transaction.currency)

                        api_client = {'color': client.color_code,
                                      'logo': self.get_logo_url(client)}

                        response_data = self.retrieve_response(
                            api_client=api_client,
                            payment_options=payment_options,
                            tabbypg_config=tabbypg_config,
                            checkoutpg_config=checkout_config,
                            payback_config=payback_config,
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
        api_client = kwargs.get('api_client', None)
        checkoutpg_config = kwargs.get('checkoutpg_config', None)
        tabbypg_config = kwargs.get('tabbypg_config', None)
        payback_config = kwargs.get('payback_config', None)
        transaction = kwargs.get('transaction', None)
        announcements_dict = kwargs.get('announcements_dict', None)
        status_code = kwargs.get('status_code', None)

        amount = None
        currency = None
        service_fee = None
        VAT_amount = None
        base_amount = None
        redirect_url = None

        cart_amount = None
        cart_currency = None
        cart_service_fee = None
        cart_base_amount = None
        cart_VAT_amount = None

        if transaction:
            amount = transaction.amount
            currency = transaction.currency
            service_fee = transaction.service_fee
            VAT_amount = transaction.VAT_amount
            base_amount = transaction.base_amount

            cart_amount = transaction.cart_amount
            cart_currency = transaction.cart_currency
            cart_service_fee = transaction.cart_service_fee
            cart_base_amount = transaction.cart_base_amount
            cart_VAT_amount = transaction.cart_VAT_amount

            if transaction.payment_status == PAYMENT_STATUS_PAID:
                redirect_url = transaction.success_url

            if transaction.payment_status in self.list_failure_statuses:
                redirect_url = transaction.failure_url

            if transaction.payment_status == PAYMENT_STATUS_CANCELLED:
                redirect_url = transaction.cancel_url

            # add transaction id in response
            if redirect_url:
                redirect_url = (redirect_url + '?transaction_id=' +
                                str(transaction.transaction_id))

        response_data = {
            "data": {
                "api_client": api_client,
                "payment_options": payment_options,
                "checkoutpg_config": checkoutpg_config,
                "b2cpayback_config": payback_config,
                "tabbypg_config": tabbypg_config,

                "amount": amount,
                "currency": currency,
                "service_fee": service_fee,
                "vat_amount": VAT_amount,
                "base_amount": base_amount,

                "cart_amount": cart_amount,
                "cart_currency": cart_currency,
                "cart_service_fee": cart_service_fee,
                "cart_vat_amount": cart_VAT_amount,
                "cart_base_amount": cart_base_amount,

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

    def get_tabby_conf(self, tabbypg_obj=None):
        tabbypg_config = {}
        if tabbypg_obj:
            tabbypg_config[
                "validation_json"] = tabbypg_obj.validation_json
        return tabbypg_config

    def get_logo_url(self, client):
        if client.logo_file and hasattr(client.logo_file, 'url'):
            return client.logo_file.url
        else:
            return None
