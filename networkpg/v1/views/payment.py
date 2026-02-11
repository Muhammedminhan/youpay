import logging
import json

from django.db import transaction
from django.utils.text import capfirst
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.utils import decrypt_string
from core.utils import get_app_config
from services.v1.views.common import add_payment_gateway_info_in_url

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
    PAYMENT_STATUS_REJECTED,
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
        self.transaction_id = request.data.get("transaction_id")
        self.decrypted_id = decrypt_string(self.transaction_id)
        logger.info(f"Received Network charge calculation request for "
                    f"Transaction ID: {self.decrypted_id}")

        transaction_obj = self.get_youpay_transaction_data(self.decrypted_id)
        if transaction_obj:
            serializer = YouPayTransactionDataSerializer(transaction_obj)
            data = serializer.data

        try:
            payment_serializer = PaymentInitiationSerializer(data=data)
            payment_serializer.is_valid(raise_exception=True)
            network_tx = NetworkTransaction.objects.create(
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
            payment_data = {
                "amount": int(float(data["amount"]) * 100),
                "currency": data["currency"],
                "email": data["customer_email"],
                "customer_name": data["customer_name"],
                "payment_reference": data["transaction_id"],
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

                    network_tx.network_order_id = order_id
                    network_tx.network_order_reference = response.get(
                        "referrer"
                    )
                    network_tx.status = PaymentStatus.STARTED
                    network_tx.save()
                    self.update_youpay_transaction_data(
                        self.prepare_data_to_update(network_tx))

                    return Response(
                        {
                            "payment_url": payment_url,
                            "order_id": order_id,
                            "payment_reference": payment_serializer["payment_reference"].value,
                            "status": "STARTED",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    logger.error("Failed to initiate Network payment: %s", response)
                    network_tx.status = PaymentStatus.FAILED
                    network_tx.save()
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
        transaction_id = request.query_params.get("transaction_id")
        self.decrypted_id = decrypt_string(transaction_id)
        if not self.decrypted_id:
            return Response(
                {"error": "transaction_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        network_tx = NetworkTransaction.objects.get(
            youpay_transaction__transaction_id=self.decrypted_id)
        response = self.client.get_order_status(network_tx.network_order_id)
        self.create_youpay_to_payment_gateways_data(
            transaction_obj=network_tx.youpay_transaction,
            transaction_id=network_tx.youpay_transaction.transaction_id,
            request_data=json.dumps(network_tx.network_order_id),
            response_data=json.dumps(response),
            request_method=REQUEST_METHOD_GET,
            request_type=PAYMENT_REQUEST_VERIFY,
        )
        if response:
            return self.process_payment_response(response, network_tx)

        data = self.response_obj.get_404_message(
                    message="Failed to fetch order details from gateway")
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def process_payment_response(self, ni_response, network_tx):
        """
        Process the payment response from Network International.
        """
        order_reference = ni_response.get('reference')
        try:
            serializer = NetworkTransactionSerializer(network_tx)
            response = serializer.save_ni_response(ni_response)
            self.update_youpay_transaction_data(
                self.prepare_data_to_update(network_tx, ni_response))
            code = response.get('code')
            return Response(
                self.response_obj.get_success_dict(
                    code=code, success_dict=response),
                status=status.HTTP_200_OK
            )
        except NetworkTransaction.DoesNotExist:
            logger.error(
                f"NetworkTransaction not found for order_id: {order_reference}")

    def prepare_data_to_update(self, network_tx, ni_response=None):
        """
        Prepares a dictionary of fields to update the YouPayTransaction table.
        """
        payment_status = PAYMENT_STATUS_PENDING
        if network_tx.status in [PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED]:
            payment_status = PAYMENT_STATUS_PAID
        elif network_tx.status == PaymentStatus.FAILED:
            payment_status = PAYMENT_STATUS_REJECTED
        data_to_update = {
            'transaction_id': self.decrypted_id,
            "payment_status": payment_status,
            "payment_reference": network_tx.payment_reference,
            "payment_method": PAYMENT_METHOD_NETWORK_CARD,
            "payment_gateway": self.payment_gateway,
        }
        if ni_response:
            data_to_update.update({
                "card_bin": network_tx.card_bin,
                "card_last4": network_tx.card_last4,
                "payment_scheme": capfirst(network_tx.card_scheme.lower()),
                "name_on_card": network_tx.card_holder_name,
                "card_issuer_country": network_tx.card_issuer_country,
                "approved": network_tx.is_approved
            })

        return data_to_update
