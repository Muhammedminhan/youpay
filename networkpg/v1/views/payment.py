import logging
import json

from django.db import transaction
from django.utils.text import capfirst
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.utils import decrypt_string
from core.utils import get_app_config
from services.v1.views.common import (
    add_payment_gateway_info_in_url,
    is_redirect
)

from integrations.constants import NETWORK_HUB_CODE

from payments.serializers.youpay_payments import (
    YouPayTransactionDataSerializer)

from networkpg.choices import PaymentStatus
from networkpg.libs.client import NetworkPGClient
from networkpg.models import NetworkTransaction
from services.v1.views.payment_handlers import PaymentHandlers

from core.response_messages import YouPayResponse

from networkpg.v1.serializers.payment import (
    PaymentInitiationSerializer, NetworkTransactionSerializer)
from core.constants import (
    REQUEST_METHOD_POST, REQUEST_METHOD_GET, PAYMENT_GATEWAY_NETWORK_IN
)   
from integrations.constants import (
    PAYMENT_REQUEST_TYPE_PAYMENT, PAYMENT_REQUEST_VERIFY
)
from payments.constants import (
    PAYMENT_METHOD_NETWORK_CARD,
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_DECLINED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_CANCELLED
)

logger = logging.getLogger(__name__)


class NetworkPaymentsApi(APIView, PaymentHandlers):
    """
    View to initiate a payment with Network International.
    """
    client = NetworkPGClient()
    response_obj = YouPayResponse()

    def __init__(self):
        self.payment_status = None
        self.transaction_id = None
        self.reference_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_NETWORK_IN
        self.decrypted_id = None

    def post(self, request, *_args, **_kwargs):
        return self.initiate_payment(request.data.get("transaction_id"))

    def initiate_payment(self, transaction_id):
        """
        This method decrypts the transaction ID, validates the transaction data,
        creates a local NetworkTransaction record, and calls the Network International
        API to create an order and obtain a payment URL for the customer.
        """
        self.transaction_id = transaction_id
        self.decrypted_id = decrypt_string(self.transaction_id)
        logger.info(
            "Received Network charge calculation request for Transaction ID: %s",
            self.decrypted_id
        )

        transaction_obj = self.get_youpay_transaction_data(self.decrypted_id)
        if transaction_obj:
            serializer = YouPayTransactionDataSerializer(transaction_obj)
            data = serializer.data

        try:
            payment_serializer = PaymentInitiationSerializer(data=data)
            payment_serializer.is_valid(raise_exception=True)
            network_transaction = NetworkTransaction.objects.create(
                **payment_serializer.validated_data,
                youpay_transaction=transaction_obj,
                status=PaymentStatus.PENDING,
            )
            app_config = get_app_config()
            params = '?id=' + self.transaction_id

            redirect_url = add_payment_gateway_info_in_url(
                transaction_data=data,
                app_config=app_config, params=params,
                code=NETWORK_HUB_CODE)
            payment_reference = payment_serializer.validated_data.get(
                'payment_reference'
            )
            payment_data = {
                "amount": int(float(data["amount"]) * 100),
                "currency": data["currency"],
                "email": data["customer_email"],
                "customer_name": data["customer_name"],
                "payment_reference": payment_reference,
                "redirect_url": redirect_url
            }
            with transaction.atomic():
                response = self.client.create_order(payment_data)
                self.create_youpay_to_payment_gateways_data(
                    transaction_obj=transaction_obj,
                    transaction_id=self.transaction_id,
                    request_data=json.dumps(payment_data),
                    response_data=json.dumps(response),
                    request_method=REQUEST_METHOD_POST,
                    request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
                )
                if response and "_links" in response:
                    payment_url = response["_links"]["payment"]["href"]
                    order_id = response["reference"]

                    network_transaction.network_order_id = order_id
                    network_transaction.network_order_reference = response.get(
                        "referrer"
                    )
                    network_transaction.status = PaymentStatus.INITIATED
                    network_transaction.save()

                    return Response(
                        {
                            "payment_url": payment_url,
                            "order_id": order_id,
                            "payment_reference": payment_reference,
                            "status": PaymentStatus.INITIATED,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    logger.error("Failed to initiate Network payment: %s", response)
                    network_transaction.status = PaymentStatus.FAILED
                    network_transaction.save()
                    message = self.response_obj.get_error_dict(error_code=1004)
                    return Response(
                        message,
                        status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Internal error during payment initiation %s", e)
            return Response(
                self.response_obj.get_error_dict(error_code=1004),
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, *_args, **_kwargs):
        """
        Retrieves the status of a payment from Network International using the
        transaction ID, updates the local transaction record, and returns the
        payment status.
        """
        transaction_id = request.query_params.get("transaction_id")
        self.decrypted_id = decrypt_string(transaction_id)
        if not self.decrypted_id:
            return Response(
                {"error": "transaction_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            network_transaction = NetworkTransaction.objects.filter(
                youpay_transaction__transaction_id=self.decrypted_id).first()
            if network_transaction.youpay_transaction.payment_status in [PAYMENT_STATUS_CANCELLED]:
                _, response = is_redirect(
                    self.decrypted_id, {},
                )
                return Response(
                    response,
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error("Internal error during payment status retrieval %s", e)
            return Response(
                {"error": "Network transaction not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        response = self.client.get_order_status(network_transaction.network_order_id)
        self.create_youpay_to_payment_gateways_data(
            transaction_obj=network_transaction.youpay_transaction,
            transaction_id=network_transaction.youpay_transaction.transaction_id,
            request_data=json.dumps(network_transaction.network_order_id),
            response_data=json.dumps(response),
            request_method=REQUEST_METHOD_GET,
            request_type=PAYMENT_REQUEST_VERIFY,
        )
        if response:
            return self.process_payment_response(response, network_transaction)

        data = self.response_obj.get_404_message(
                    message="Failed to fetch order details from gateway")
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def process_payment_response(self, ni_response, network_transaction):
        """
        Process the payment response from Network International.
        """
        order_reference = ni_response.get('reference')
        try:
            serializer = NetworkTransactionSerializer(network_transaction)
            response = serializer.save_ni_response(ni_response)
            self.update_youpay_transaction_data(
                self.prepare_data_to_update(network_transaction))

            code = response.get('code')
            return Response(
                self.response_obj.get_success_dict(
                    code=code, success_dict=response),
                status=status.HTTP_200_OK
            )
        except NetworkTransaction.DoesNotExist:
            logger.error(
                f"NetworkTransaction not found for order_id: {order_reference}")

    def prepare_data_to_update(self, network_transaction, ni_response=None):
        """
        Prepares a dictionary of fields to update the YouPayTransaction table.
        """
        payment_status = PAYMENT_STATUS_PENDING
        if network_transaction.status in [PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED]:
            payment_status = PAYMENT_STATUS_PAID
        elif network_transaction.status == PaymentStatus.FAILED:
            payment_status = PAYMENT_STATUS_FAILED
        elif network_transaction.status in [PaymentStatus.DECLINED,]:
            payment_status = PAYMENT_STATUS_DECLINED
        data_to_update = {
            'transaction_id': self.decrypted_id,
            "payment_status": payment_status,
            "payment_reference": network_transaction.payment_reference,
            "payment_method": PAYMENT_METHOD_NETWORK_CARD,
            "payment_gateway": self.payment_gateway,
        }
        if ni_response:
            data_to_update.update({
                "card_bin": network_transaction.card_bin,
                "card_last4": network_transaction.card_last4,
                "payment_scheme": capfirst(network_transaction.card_scheme.lower()),
                "name_on_card": network_transaction.card_holder_name,
                "card_issuer_country": network_transaction.card_issuer_country,
                "approved": network_transaction.is_approved
            })

        return data_to_update
