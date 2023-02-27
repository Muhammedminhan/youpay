import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.response_messages import YouPayResponse
from core.utils import (decrypt_string, get_gateway_additional_fee,
                        decimal_rounded)
from integrations.models import PaymentGateway
from integrations.v1.gateway_clients.b2c_payback import B2CPaybackManager
from integrations.v1.gateway_clients.checkoutpg import CheckoutpgManager
from integrations.v1.gateway_clients.tabbypg import TabbyPGManager
from services.constants import TOKEN_TYPE_PAYPAL
from payments.constants import (
    PAYMENT_STATUS_ERROR,
    PAYMENT_STATUS_REJECTED,
    PAYMENT_STATUS_VOIDED,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_FLAGGED,
    PAYMENT_STATUS_PAID
)
from services.v1.views.common import YouPayTransactionCRUD
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
        b2c_payback_obj = B2CPaybackManager()

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
                        gateways = client.payment_gateway.filter(
                            is_active=True)
                        payback_config = b2c_payback_obj.get_configurations(
                            transaction.amount, transaction.currency)
                        payment_options = get_payment_options(
                            transaction, gateways, payback_config)
                        announcements_dict = get_announcements(
                            transaction.platform)
                        api_client = {'color': client.color_code,
                                      'mobile_logo': get_mobile_logo_url(
                                          client),
                                      'logo': get_logo_url(client)}

                        paypal_config = self.get_paypal_config(
                            payment_options, transaction)

                        response_data = self.retrieve_response(
                            api_client=api_client,
                            payment_options=payment_options,
                            tabbypg_config=tabbypg_config,
                            checkoutpg_config=checkout_config,
                            payback_config=payback_config,
                            paypal_config=paypal_config,
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
        paypal_config = kwargs.get('paypal_config', None)
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
                "paypal_config": paypal_config,

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

    def get_paypal_config(self, payment_option, transaction_obj):
        """
        returns paypal process fee config
        only if paypal is enabled
        """
        paypal_config = {}
        paypal_enabled = payment_option.get('paypal', False)
        if paypal_enabled:
            additional_fee = get_gateway_additional_fee(TOKEN_TYPE_PAYPAL)
            paypal_config["processing_fee_json"] = (
                self.calculate_additional_charges(
                    additional_fee, transaction_obj) if additional_fee else {})
        return paypal_config

    def calculate_processing_fee(self, additional_fee, base_amount,
                                 vat_percent):
        """
        Calulate proccessing fee and vat percentage for processing fee
        """
        processing_fee = 0
        percentage = additional_fee.percentage
        fixed_amount = additional_fee.fixed_amount
        if percentage:
            processing_fee += base_amount * (percentage/100)
        if fixed_amount:
            processing_fee += fixed_amount

        processing_fee_vat = vat_percent * processing_fee
        return processing_fee, processing_fee_vat

    def update_youpay_transaction_data(self, data, transaction_id):
        """
        Update transaction table with calculated value
        """
        dct_transaction_data = {
            "transaction_id": transaction_id
        }
        dct_transaction_data.update(data)
        transaction_crud = YouPayTransactionCRUD()
        transaction_crud.update_youpay_transaction_data(dct_transaction_data)

    def calculate_additional_charges(self, additional_fee, transaction):
        """
        method to calculate new vat amount
        based on the additional charges for paypal
        """
        dct_processing_fee = {}
        try:
            order_amount = transaction.base_amount
            service_fee = transaction.service_fee
            decimal_notation = transaction.paypal_currency_decimal_notation
            vat_percent = (transaction.paypal_vat_percentage/100)
            processing_fee, processing_fee_vat = self.calculate_processing_fee(
                additional_fee, order_amount, vat_percent
            )
            processing_fee = decimal_rounded(processing_fee, decimal_notation)
            processing_fee_vat = decimal_rounded(processing_fee_vat,
                                                 decimal_notation)
            vat_amount = vat_percent * (service_fee + processing_fee)
            vat_amount = decimal_rounded(vat_amount, decimal_notation)
            total_amount = (order_amount + service_fee +
                            processing_fee + vat_amount)
            total_amount = decimal_rounded(total_amount, decimal_notation)
            dct_processing_fee = {
                "order_amount": order_amount,
                "processing_fee": processing_fee,
                "processing_fee_vat": processing_fee_vat,
                "new_vat": vat_amount,
                "service_fee": service_fee,
                "total_amount": total_amount
            }
            self.update_youpay_transaction_data(dct_processing_fee,
                                                transaction.transaction_id)
        except Exception as e:
            logger.error("Exception occurred during paypal "
                         "processing fee calculation {}".format(str(e)))
        return dct_processing_fee


class ClientStaticFilesAPI(APIView):
    """
    Static files view
    """

    def get(self, request):
        """
        Get static files
        """
        response_obj = YouPayResponse()

        transaction_id = decrypt_string(request.GET.get('id', None))

        try:

            transaction_obj = YouPayTransactionData.objects.get(
                transaction_id=transaction_id)

            client = transaction_obj.api_client
            if client:
                api_client_data = {
                    'color': client.color_code,
                    'mobile_logo': get_mobile_logo_url(client),
                    'logo': get_logo_url(client)
                }

                data = response_obj.get_success_dict(
                    code=response_obj.SUCCESS,
                    success_dict=api_client_data
                )

                return Response(data, status=status.HTTP_200_OK)
            else:
                logger.error("Client not found for transaction id : {}"
                             "".format(transaction_id))

                data = response_obj.get_error_dict(
                    error_code=response_obj.MISSING_CLIENT_INFO)
                return Response(data.get('errors'),
                                status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            message = str(e)
            logger.error("Exception occurred while retrieving static files "
                         "for transaction {} : {}  ".format(transaction_id,
                                                            message))
            data = response_obj.get_404_message(message=str(e))
            return Response(
                data,
                status=status.HTTP_404_NOT_FOUND)


def get_logo_url(client):
    if client.logo_file and hasattr(client.logo_file, 'url'):
        return client.logo_file.url
    else:
        return None


def get_mobile_logo_url(client):
    if client.mobile_logo_file and hasattr(client.mobile_logo_file,
                                           'url'):
        return client.mobile_logo_file.url
    else:
        return None
